"""
Advisor model with enhanced OOP methods - Updated for multiple teams
"""

from sqlalchemy import or_, and_
from app.models import db
from app.models.base import BaseModel

class AdvisorGoal(BaseModel):
    """Company-specific yearly goals for advisors"""
    __tablename__ = 'advisor_goals'
    
    advisor_id = db.Column(db.Integer, db.ForeignKey('advisors.id'), nullable=False)
    company = db.Column(db.String(50), nullable=False)
    yearly_goal = db.Column(db.Float, default=50000.0)
    
    # Unique constraint to prevent duplicate goals per company
    __table_args__ = (db.UniqueConstraint('advisor_id', 'company', name='unique_advisor_company_goal'),)

class Advisor(BaseModel):
    """Advisor model with enhanced OOP methods for multiple teams"""
    __tablename__ = 'advisors'
    
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_master = db.Column(db.Boolean, default=False)
    is_hidden_from_team = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships
    team_memberships = db.relationship('AdvisorTeam', backref='advisor', cascade='all, delete-orphan')
    submissions = db.relationship('Submission', backref='advisor')
    paid_cases = db.relationship('PaidCase', backref='advisor')
    yearly_goals = db.relationship('AdvisorGoal', backref='advisor', cascade='all, delete-orphan')
    
    def get_teams_for_company(self, company):
        """Get ALL teams for a specific company"""
        teams = []
        for membership in self.team_memberships:
            if membership.team.company == company:
                teams.append(membership.team)
        return teams
    
    def get_visible_team_for_company(self, company):
        """Get the visible (non-hidden) team for a specific company"""
        for membership in self.team_memberships:
            if membership.team.company == company and not membership.team.is_hidden:
                return membership.team
        return None
    
    def get_primary_team_for_company(self, company):
        """Get primary team for a company (visible team first, then any team)"""
        # First try to get a visible team
        visible_team = self.get_visible_team_for_company(company)
        if visible_team:
            return visible_team
        
        # If no visible team, return any team
        teams = self.get_teams_for_company(company)
        return teams[0] if teams else None
    
    def get_team_for_company(self, company):
        """Backward compatibility - returns primary team"""
        return self.get_primary_team_for_company(company)
    
    def is_in_hidden_team_only(self, company):
        """Check if advisor is only in hidden teams for this company"""
        teams = self.get_teams_for_company(company)
        if not teams:
            return False
        return all(team.is_hidden for team in teams)
    
    def get_yearly_goal_for_company(self, company):
        """Get yearly goal for a specific company - checks team first, then individual goal"""
        # First check if they're in a team with a goal (prefer visible teams)
        visible_team = self.get_visible_team_for_company(company)
        if visible_team:
            for membership in self.team_memberships:
                if membership.team.id == visible_team.id and membership.yearly_goal > 0:
                    return membership.yearly_goal
        
        # Then check any team goal
        for membership in self.team_memberships:
            if membership.team.company == company and membership.yearly_goal > 0:
                return membership.yearly_goal
        
        # Then check individual goal
        for goal in self.yearly_goals:
            if goal.company == company:
                return goal.yearly_goal
        
        # Default goal if none set
        return 50000.0
    
    def set_yearly_goal_for_company(self, company, goal_amount):
        """Set yearly goal for a specific company"""
        # If they're in a team, update the primary team goal
        primary_team = self.get_primary_team_for_company(company)
        
        if primary_team:
            team_membership = None
            for membership in self.team_memberships:
                if membership.team.id == primary_team.id:
                    team_membership = membership
                    break
            
            if team_membership:
                team_membership.yearly_goal = float(goal_amount)
        else:
            # Update or create individual goal
            individual_goal = None
            for goal in self.yearly_goals:
                if goal.company == company:
                    individual_goal = goal
                    break
            
            if individual_goal:
                individual_goal.yearly_goal = float(goal_amount)
            else:
                new_goal = AdvisorGoal(
                    advisor_id=self.id,
                    company=company,
                    yearly_goal=float(goal_amount)
                )
                db.session.add(new_goal)
        
        db.session.commit()
        return True
    
    def get_submissions_for_period(self, company, start_date, end_date, valid_types=None):
        """Get submissions for a specific period and company"""
        from app.models.submission import Submission
        
        query = Submission.query.filter(
            and_(
                Submission.submission_date >= start_date,
                Submission.submission_date <= end_date,
                Submission.company == company,
                or_(
                    Submission.advisor_id == self.id,
                    and_(Submission.advisor_id.is_(None), Submission.advisor_name == self.full_name)
                )
            )
        )
        
        submissions = query.all()
        if valid_types:
            return [s for s in submissions if s.business_type in valid_types]
        return submissions
    
    def get_paid_cases_for_period(self, company, start_date, end_date, valid_types=None):
        """Get paid cases for a specific period and company"""
        from app.models.paid_case import PaidCase
        
        query = PaidCase.query.filter(
            and_(
                PaidCase.date_paid >= start_date,
                PaidCase.date_paid <= end_date,
                PaidCase.company == company,
                or_(
                    PaidCase.advisor_id == self.id,
                    and_(PaidCase.advisor_id.is_(None), PaidCase.advisor_name == self.full_name)
                )
            )
        )
        
        cases = query.all()
        if valid_types:
            return [c for c in cases if c.case_type in valid_types]
        return cases
    
    def calculate_metrics_for_period(self, company, start_date, end_date, valid_submission_types=None, valid_case_types=None):
        """Calculate comprehensive metrics for a period with enhanced avg case size"""
        submissions = self.get_submissions_for_period(company, start_date, end_date, valid_submission_types)
        paid_cases = self.get_paid_cases_for_period(company, start_date, end_date, valid_case_types)
        
        # Filter submissions for valid business types and referrals
        valid_submissions = [s for s in submissions if valid_submission_types and s.business_type in valid_submission_types]
        
        # Count referrals separately - get ALL submissions without any business type filtering
        all_user_submissions = self.get_submissions_for_period(company, start_date, end_date, None)
        referrals_made = len([s for s in all_user_submissions if s.business_type == 'Referral'])
        
        # Calculate totals
        total_submitted = sum((s.expected_proc or 0) + (s.expected_fee or 0) for s in valid_submissions)
        total_fee = sum(s.expected_fee or 0 for s in valid_submissions)
        total_paid = sum(p.value for p in paid_cases)
        
        # Calculate applications breakdown
        applications = {}
        for submission in valid_submissions:
            if submission.business_type not in applications:
                applications[submission.business_type] = 0
            applications[submission.business_type] += 1
        
        # ENHANCED: Calculate new average case size using your formula
        enhanced_avg_case_size = self.calculate_enhanced_avg_case_size(
            company, start_date, end_date, valid_case_types
        )
        
        return {
            'total_submitted': total_submitted,
            'total_fee': total_fee,
            'combined_total': total_submitted,
            'total_paid': total_paid,
            'payment_percentage': (total_paid / total_submitted * 100) if total_submitted > 0 else 0,
            'applications': applications,
            'referrals_made': referrals_made,
            'submissions_count': len(valid_submissions),
            'paid_cases_count': len(paid_cases),
            # NEW: Enhanced average case size data
            'avg_case_size': enhanced_avg_case_size['avg_case_size'],
            'avg_case_size_breakdown': enhanced_avg_case_size
        }
    
    def is_visible_to_advisor(self, viewing_advisor):
        """Check if this advisor should be visible to another advisor"""
        if viewing_advisor.is_master:
            return True  # Masters can see everyone
        return not self.is_hidden_from_team  # Regular advisors can't see hidden ones

    def get_visible_team_members(self, company):
        """
        Get team members that this advisor can see
        Filters out advisors that are hidden from team (unless this advisor is a master)
        """
        team = self.get_team_for_company(company)
        if not team:
            return []
        
        visible_members = []
        for member in team.members:
            if member.is_visible_to_advisor(self):
                visible_members.append(member)
        
        return visible_members

    def calculate_enhanced_avg_case_size(self, company, start_date, end_date, valid_case_types=None):
        """
        Calculate enhanced average case size with income_type consideration and improved name matching
        """
        from app.models.paid_case import PaidCase
        from sqlalchemy import and_, or_
        from collections import defaultdict
        
        print(f"\n🔍 DEBUG: Calculating avg case size for {self.full_name} in {company}")
        print(f"📅 Period: {start_date} to {end_date}")
        
        # Get all paid cases for this advisor in the period
        query = PaidCase.query.filter(
            and_(
                PaidCase.date_paid >= start_date,
                PaidCase.date_paid <= end_date,
                PaidCase.company == company,
                or_(
                    PaidCase.advisor_id == self.id,
                    and_(PaidCase.advisor_id.is_(None), PaidCase.advisor_name == self.full_name)
                )
            )
        )
        
        all_cases = query.all()
        # Filter cases for calculation - this filter is for valid case types (usually both residential and insurance)
        if valid_case_types:
            filtered_cases = [c for c in all_cases if c.case_type in valid_case_types]
        else:
            filtered_cases = all_cases
        
        
        # Get ONLY residential cases for total_paid calculation and unique counting
        residential_cases = [case for case in filtered_cases 
                            if 'residential' in case.case_type.lower()]
        
        for case in residential_cases:
            income_info = f" (Income: {getattr(case, 'income_type', 'N/A')})" if hasattr(case, 'income_type') else ""
        
        # Calculate total paid (sum of ONLY RESIDENTIAL case values)
        total_paid = sum(case.value for case in residential_cases)
        
        # ENHANCED: Count unique mortgage applications with income_type consideration
        unique_mortgage_applications = self._count_unique_mortgage_applications_with_income_type(residential_cases)
        
        # Calculate insurance referral values with enhanced name matching
        insurance_referred_to_me = 0  # Insurance VALUE where who_referred contains my name
        insurance_advisor_referred_to_me = 0  # Insurance VALUE where who_referred contains another advisor's name
        
        # Get all advisor names from company config for comparison
        from app.config import config_manager
        company_config = config_manager.get_company_config(company)
        all_advisor_names = company_config.advisor_names if company_config else []
        
        # Use ALL cases for insurance referrals, not just filtered ones
        insurance_cases = [case for case in query.all() if 'insurance' in case.case_type.lower()]
        
        for case in insurance_cases:
            # ENHANCED: Use improved name matching that handles Mike vs Michael
            if case.who_referred:
                if self._enhanced_name_matches_referral(case.who_referred, company_config):
                    insurance_referred_to_me += case.value
                    print(f"     ✅ REFERRED TO ME: +£{case.value}")
                elif self._is_other_advisor_referral_enhanced(case.who_referred, all_advisor_names, company_config):
                    insurance_advisor_referred_to_me += case.value
                    print(f"     ⚠️ OTHER ADVISOR REFERRED TO ME: +£{case.value}")
                else:
                    print(f"     ❓ Has referral but no match: '{case.who_referred}'")

        
        
        # Apply the CORRECT formula:
        # avg_case_size = (total_paid / unique_mortgage_applications) + insurance_referred_to_me - insurance_advisor_referred_to_me
        
        if unique_mortgage_applications > 0:
            avg_per_mortgage = total_paid / unique_mortgage_applications
            avg_case_size = avg_per_mortgage + insurance_referred_to_me - insurance_advisor_referred_to_me
        else:
            avg_per_mortgage = 0
            avg_case_size = 0 + insurance_referred_to_me - insurance_advisor_referred_to_me
        
        
        return {
            'avg_case_size': round(avg_case_size, 2),
            'total_paid': total_paid,
            'unique_mortgage_applications': unique_mortgage_applications,
            'avg_per_mortgage': round(avg_per_mortgage, 2) if unique_mortgage_applications > 0 else 0,
            'insurance_referred_to_me': insurance_referred_to_me,
            'insurance_advisor_referred_to_me': insurance_advisor_referred_to_me,
            'total_cases': len(query.all()),  # All cases
            'filtered_cases_count': len(filtered_cases),  # Valid case types
            'residential_cases_count': len(residential_cases),  # Only residential
            'formula_breakdown': {
                'step1_avg_per_mortgage': round(avg_per_mortgage, 2) if unique_mortgage_applications > 0 else 0,
                'step2_plus_insurance_referred_to_me': insurance_referred_to_me,
                'step3_minus_insurance_advisor_referred_to_me': insurance_advisor_referred_to_me,
                'final_result': round(avg_case_size, 2)
            }
        }

    def _is_other_advisor_referral(self, who_referred_text, all_advisor_names):
        """
        Check if who_referred text contains another advisor's name (not this advisor's name)
        """
        if not who_referred_text:
            return False
        
        who_referred_lower = who_referred_text.lower()
        
        # Check if it contains this advisor's name first - if so, it's not another advisor
        if self._name_matches_referral(who_referred_text):
            return False
        
        # Check if it contains any other advisor's name
        for advisor_name in all_advisor_names:
            if advisor_name.lower() != self.full_name.lower():  # Skip current advisor
                advisor_name_lower = advisor_name.lower()
                
                # Check full name match
                if advisor_name_lower in who_referred_lower:
                    return True
                
                # Check first name match (if longer than 2 chars)
                first_name = advisor_name_lower.split()[0] if advisor_name_lower else ""
                if first_name and len(first_name) > 2 and first_name in who_referred_lower:
                    return True
                
                # Check last name match (if longer than 2 chars)
                last_name = advisor_name_lower.split()[-1] if advisor_name_lower and len(advisor_name_lower.split()) > 1 else ""
                if last_name and len(last_name) > 2 and last_name in who_referred_lower:
                    return True
        
        return False
    def _count_unique_mortgage_applications(self, residential_cases):
        """
        DEBUG version that prints detailed information about unique counting
        """
        from collections import defaultdict
                
        # Group cases by customer name
        customer_cases = defaultdict(list)
        for case in residential_cases:
            if case.customer_name:
                # Normalize customer name (remove extra spaces, make lowercase for comparison)
                normalized_name = ' '.join(case.customer_name.strip().split()).lower()
                customer_cases[normalized_name].append(case.value)
                
        unique_count = 0
        
        for customer_name, values in customer_cases.items():
            
            if len(values) == 1:
                # Single case = 1 unique application
                unique_count += 1
            else:
                # Multiple cases - check for the special pattern
                
                # Check if we have the specific pattern: positive, negative, different positive
                has_special_pattern = False
                
                if len(values) >= 3:
                    # Look for value/negative value pairs
                    positive_values = [v for v in values if v > 0]
                    negative_values = [v for v in values if v < 0]
                    

                    
                    # Check if any positive value has a corresponding negative
                    for pos_val in positive_values:
                        if -pos_val in negative_values:
                            has_special_pattern = True
                            break
                
                if has_special_pattern:
                    unique_count += 1
                else:
                    # No special pattern found - count as separate applications
                    unique_applications = len(set(abs(v) for v in values if v != 0))
                    unique_count += unique_applications
        
        return unique_count

    def _name_matches_referral(self, who_referred_text):
        """Check if who_referred text contains this advisor's name"""
        if not who_referred_text or not self.full_name:
            return False
        
        who_referred_lower = who_referred_text.lower()
        advisor_name_lower = self.full_name.lower()
        
        # Direct full name match
        if advisor_name_lower in who_referred_lower:
            return True
        
        # Check first name match
        first_name = advisor_name_lower.split()[0] if advisor_name_lower else ""
        if first_name and len(first_name) > 2 and first_name in who_referred_lower:
            return True
        
        # Check last name match
        last_name = advisor_name_lower.split()[-1] if advisor_name_lower and len(advisor_name_lower.split()) > 1 else ""
        if last_name and len(last_name) > 2 and last_name in who_referred_lower:
            return True
        
        return False
    
    def calculate_metrics_for_period(self, company, start_date, end_date, valid_submission_types=None, valid_case_types=None):
        """Calculate comprehensive metrics for a period with enhanced avg case size"""
        submissions = self.get_submissions_for_period(company, start_date, end_date, valid_submission_types)
        paid_cases = self.get_paid_cases_for_period(company, start_date, end_date, valid_case_types)
        
        # Filter submissions for valid business types and referrals
        valid_submissions = [s for s in submissions if valid_submission_types and s.business_type in valid_submission_types]
        
        # Count referrals separately - get ALL submissions without any business type filtering
        all_user_submissions = self.get_submissions_for_period(company, start_date, end_date, None)
        referrals_made = len([s for s in all_user_submissions if s.business_type == 'Referral'])
        
        # Calculate totals
        total_submitted = sum((s.expected_proc or 0) + (s.expected_fee or 0) for s in valid_submissions)
        total_fee = sum(s.expected_fee or 0 for s in valid_submissions)
        total_paid = sum(p.value for p in paid_cases)
        
        # Calculate applications breakdown
        applications = {}
        for submission in valid_submissions:
            if submission.business_type not in applications:
                applications[submission.business_type] = 0
            applications[submission.business_type] += 1
        
        # ENHANCED: Calculate new average case size using your formula
        enhanced_avg_case_size = self.calculate_enhanced_avg_case_size(
            company, start_date, end_date, valid_case_types
        )
        
        return {
            'total_submitted': total_submitted,
            'total_fee': total_fee,
            'combined_total': total_submitted,
            'total_paid': total_paid,
            'payment_percentage': (total_paid / total_submitted * 100) if total_submitted > 0 else 0,
            'applications': applications,
            'referrals_made': referrals_made,
            'submissions_count': len(valid_submissions),
            'paid_cases_count': len(paid_cases),
            # NEW: Enhanced average case size data
            'avg_case_size': enhanced_avg_case_size['avg_case_size'],
            'avg_case_size_breakdown': enhanced_avg_case_size
        }

    def _get_normalized_referrer_name(self, who_referred_text):
        """
        Get the normalized/full name of the referrer for debug purposes
        """
        if not who_referred_text:
            return "Unknown"
        
        who_referred_lower = who_referred_text.lower().strip()
        
        # Get company config for name mappings
        from app.config import config_manager
        company_config = config_manager.get_company_config('windsor')
        
        # Try to normalize using company mappings
        if company_config and hasattr(company_config, 'name_mappings'):
            for mapping_key, full_name in company_config.name_mappings.items():
                if mapping_key in who_referred_lower or who_referred_lower in mapping_key:
                    return full_name
        
        # If no mapping found, return original
        return who_referred_text
    

    def _count_unique_mortgage_applications_debug(self, residential_cases):
        """
        DEBUG version that prints detailed information about unique counting
        """
        from collections import defaultdict
        
        
        # Group cases by customer name
        customer_cases = defaultdict(list)
        for case in residential_cases:
            if case.customer_name:
                # Normalize customer name (remove extra spaces, make lowercase for comparison)
                normalized_name = ' '.join(case.customer_name.strip().split()).lower()
                customer_cases[normalized_name].append(case.value)
        
        
        unique_count = 0
        
        for customer_name, values in customer_cases.items():
            
            if len(values) == 1:
                # Single case = 1 unique application
                unique_count += 1
            else:
                # Multiple cases - check for the special pattern
                
                # Check if we have the specific pattern: positive, negative, different positive
                has_special_pattern = False
                
                if len(values) >= 3:
                    # Look for value/negative value pairs
                    positive_values = [v for v in values if v > 0]
                    negative_values = [v for v in values if v < 0]
                    
                    # Check if any positive value has a corresponding negative
                    for pos_val in positive_values:
                        if -pos_val in negative_values:
                            has_special_pattern = True
                            break
                
                if has_special_pattern:
                    unique_count += 1
                else:
                    # No special pattern found - count as separate applications
                    unique_applications = len(set(abs(v) for v in values if v != 0))
                    unique_count += unique_applications
        
        return unique_count

    def _count_unique_mortgage_applications_with_income_type(self, residential_cases):
        """
        Count unique mortgage applications: Residential cases with 'Lender Commission' income type
        """
        from collections import defaultdict
        
        print(f"Criteria: case_type='Residential' AND income_type='Lender Commission'")
        
        # Filter for BOTH Residential case type AND Lender Commission income type
        mortgage_cases = []
        for case in residential_cases:
            income_type = getattr(case, 'income_type', '')
            
            # Must be both Residential AND Lender Commission
            if income_type == 'Lender Commission':
                mortgage_cases.append(case)

        
        if len(mortgage_cases) == 0:
            return 0
        
        # Group cases by customer name
        customer_cases = defaultdict(list)
        for case in mortgage_cases:
            if case.customer_name:
                # Normalize customer name (remove extra spaces, make lowercase for comparison)
                normalized_name = ' '.join(case.customer_name.strip().split()).lower()
                customer_cases[normalized_name].append(case.value)
        
        
        unique_count = 0
        
        for customer_name, values in customer_cases.items():

            
            if len(values) == 1:
                # Single case = 1 unique application
                unique_count += 1
            else:
                # Multiple cases - check for the special pattern
                
                # Check if we have the specific pattern: positive, negative, different positive
                has_special_pattern = False
                
                if len(values) >= 3:
                    # Look for value/negative value pairs
                    positive_values = [v for v in values if v > 0]
                    negative_values = [v for v in values if v < 0]
                    
                    # Check if any positive value has a corresponding negative
                    for pos_val in positive_values:
                        if -pos_val in negative_values:
                            has_special_pattern = True
                            break
                
                if has_special_pattern:
                    unique_count += 1
                else:
                    # No special pattern found - count as separate applications
                    unique_applications = len(set(abs(v) for v in values if v != 0))
                    unique_count += unique_applications
        
        return unique_count


    def _enhanced_name_matches_referral(self, who_referred_text, company_config):
        """
        ENHANCED: Check if who_referred text matches this advisor using company name mappings
        This fixes the Mike vs Michael issue
        """
        if not who_referred_text or not self.full_name:
            return False
        
        # First normalize the referral text using company mappings
        normalized_referrer = company_config.normalize_advisor_name(who_referred_text) if company_config else who_referred_text
        # Check if normalized referrer matches this advisor's name
        if normalized_referrer and normalized_referrer.lower() == self.full_name.lower():
            return True
        
        # Fallback to original logic for backward compatibility
        who_referred_lower = who_referred_text.lower()
        advisor_name_lower = self.full_name.lower()
        
        # Direct full name match
        if advisor_name_lower in who_referred_lower:
            return True
        
        # Check first name match
        first_name = advisor_name_lower.split()[0] if advisor_name_lower else ""
        if first_name and len(first_name) > 2 and first_name in who_referred_lower:
            return True
        
        # Check last name match
        last_name = advisor_name_lower.split()[-1] if advisor_name_lower and len(advisor_name_lower.split()) > 1 else ""
        if last_name and len(last_name) > 2 and last_name in who_referred_lower:
            return True
        
        return False

    def _is_other_advisor_referral_enhanced(self, who_referred_text, all_advisor_names, company_config):
        """
        ENHANCED: Check if who_referred text contains another advisor's name using company mappings
        """
        if not who_referred_text:
            return False
        
        # First normalize the referral text using company mappings
        normalized_referrer = company_config.normalize_advisor_name(who_referred_text) if company_config else None
        
        # Check if normalized referrer is another advisor (not this advisor)
        if normalized_referrer and normalized_referrer.lower() != self.full_name.lower():
            for advisor_name in all_advisor_names:
                if advisor_name.lower() == normalized_referrer.lower():
                    return True
        
        # Fallback to original logic
        who_referred_lower = who_referred_text.lower()
        
        # Check if it contains this advisor's name first - if so, it's not another advisor
        if self._enhanced_name_matches_referral(who_referred_text, company_config):
            return False
        
        # Check if it contains any other advisor's name
        for advisor_name in all_advisor_names:
            if advisor_name.lower() != self.full_name.lower():  # Skip current advisor
                advisor_name_lower = advisor_name.lower()
                
                # Check full name match
                if advisor_name_lower in who_referred_lower:
                    return True
                
                # Check first name match (if longer than 2 chars)
                first_name = advisor_name_lower.split()[0] if advisor_name_lower else ""
                if first_name and len(first_name) > 2 and first_name in who_referred_lower:
                    return True
                
                # Check last name match (if longer than 2 chars)  
                last_name = advisor_name_lower.split()[-1] if advisor_name_lower and len(advisor_name_lower.split()) > 1 else ""
                if last_name and len(last_name) > 2 and last_name in who_referred_lower:
                    return True
        
        return False