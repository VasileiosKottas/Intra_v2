from app.controllers.base import BaseController
from app.services.report_service import ReportService
from flask import request, jsonify, send_file
import io
from datetime import date

class ReportsController(BaseController):
    """Handles report generation and exporting"""
    
    def register_routes(self):

        try:
            """Register report routes"""
            self.app.add_url_rule('/api/reports/generate', 'api.generate', 
                                self.generate_report, methods=['POST'])
            self.app.add_url_rule('/api/reports/export', 'api.export', 
                                self.export_report, methods=['GET'])
            self.app.add_url_rule('/api/reports/team-monthly-table', 'reports.team_monthly_table',
                      self.team_monthly_table, methods=['GET'])
            self.app.add_url_rule('/api/reports/team-monthly-excel', 'reports.team_monthly_excel',
                                self.team_monthly_excel, methods=['GET'])

        except Exception as e:
            print(f"❌ Error registering routes: {e}")
            import traceback
            traceback.print_exc()

    def generate_report(self):
        try:
            params = request.json or {}
            report_service = ReportService()
            report_data = report_service.generate_report()  # no params arg needed
            return jsonify({'status': 'success', 'data': report_data}), 200
        except Exception as e:
            print(f"Error generating report: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    def export_report(self):
        try:
            format = request.args.get('format', 'pdf')
            report_service = ReportService()
            report_data = report_service.generate_report()  # dict, not Response
            filename = "test.csv"
            # return CSV/PDF properly instead of jsonify-ing a Response
            return jsonify({'status': 'success', 'data': report_data, 'filename': filename}), 200
        except Exception as e:
            print(f"Error exporting report: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
        
    def team_monthly_table(self):
        team_id = request.args.get('team_id', type=int)
        if not team_id:
            return jsonify({'error': 'team_id is required'}), 400
        svc = ReportService()
        data = svc.generate_team_monthly_table(team_id)
        if isinstance(data, dict) and data.get('error'):
            return jsonify(data), 404
        return jsonify(data), 200

    def team_monthly_excel(self):
        team_id = request.args.get('team_id', type=int)
        if not team_id:
            return jsonify({'error': 'team_id is required'}), 400
        svc = ReportService()
        xlsx = svc.export_team_monthly_excel(team_id)
        filename = f"{date.today().strftime('%Y-%m')}-team-{team_id}-monthly.xlsx"
        return send_file(
            io.BytesIO(xlsx),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename
        )