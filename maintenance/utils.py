from django.db.models import Sum

from .models import MaintenanceChoices, ServiceChoices


class ReportSummarizer:
    TOTAL_MAINTENANCE = "total_maintenance"
    TOTAL_MAINTENANCE_COST = "total_maintenance_cost"
    PREVENTIVE = "preventive"
    PREVENTIVE_COST = "preventive_cost"
    CURATIVE = "curative"
    CURATIVE_COST = "curative_cost"
    TOTAL_SERVICE_COST = "total_service_cost"
    MECHANIC = "mechanic"
    ELECTRICIAN = "electrician"
    CLEANING = "cleaning"

    def summarize_reports(self, maintenance_reports):
        report = self.initialize_report_summary()

        for maintenance_report in maintenance_reports:
            self.update_total_maintenance(report)
            self.update_costs(report, maintenance_report)
            self.update_maintenance_type_counts(report, maintenance_report)
            self.update_service_provider_counts(report, maintenance_report)

        return report

    def initialize_report_summary(self):
        return {
            self.TOTAL_MAINTENANCE: 0,
            self.TOTAL_MAINTENANCE_COST: 0,
            self.PREVENTIVE: 0,
            self.PREVENTIVE_COST: 0,
            self.CURATIVE: 0,
            self.CURATIVE_COST: 0,
            self.TOTAL_SERVICE_COST: 0,
            self.MECHANIC: 0,
            self.ELECTRICIAN: 0,
            self.CLEANING: 0,
        }

    def update_total_maintenance(self, report):
        report[self.TOTAL_MAINTENANCE] += 1

    def update_costs(self, report, maintenance_report):
        report[self.TOTAL_MAINTENANCE_COST] += maintenance_report.total_cost
        report[self.TOTAL_SERVICE_COST] += maintenance_report.service_provider_events.aggregate(Sum('cost'))["cost__sum"] or 0

    def update_maintenance_type_counts(self, report, maintenance_report):
        if maintenance_report.maintenance_type == MaintenanceChoices.PREVENTIVE:
            report[self.PREVENTIVE] += 1
            report[self.PREVENTIVE_COST] += maintenance_report.total_cost
        elif maintenance_report.maintenance_type == MaintenanceChoices.CURATIVE:
            report[self.CURATIVE] += 1
            report[self.CURATIVE_COST] += maintenance_report.total_cost

    def update_service_provider_counts(self, report, maintenance_report):
        service_type_mapping = {
            ServiceChoices.MECHANIC: self.MECHANIC,
            ServiceChoices.ELECTRICIAN: self.ELECTRICIAN,
            ServiceChoices.CLEANING: self.CLEANING,
        }
        for service_provider_event in maintenance_report.service_provider_events.all():
            service_type = service_provider_event.service_provider.service_type
            if service_type in service_type_mapping:
                report[service_type_mapping[service_type]] += 1
