from django.core.management.base import BaseCommand, CommandError

from information.live_data import landing_sources


class Command(BaseCommand):
    help = "Refresh the public UN SDG indicators and SDG.org data hubs."

    def handle(self, *args, **options):
        result = landing_sources(refresh=True, force=True)
        resources = [result["world_bank"], result["hubs"], *result["indicators"]]
        for item in result["indicators"]:
            self.stdout.write(f"{item['title']}: {item['area_count']} areas ({item['status']})")
        if any(row["status"] != "fresh" for row in resources):
            raise CommandError("Some sources could not refresh. Last successful data has been retained.")
        self.stdout.write(self.style.SUCCESS("All sources refreshed."))
