import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import PendingRegistration

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Deletes PendingRegistration rows that have expired without "
        "completing phone verification. Safe to run frequently — no real "
        "User/School data is ever affected, since nothing real exists "
        "until verification succeeds."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        now = timezone.now()

        stale = PendingRegistration.objects.filter(expires_at__lt=now)
        count = stale.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No expired pending registrations found."))
            return

        if dry_run:
            self.stdout.write(f"Would delete {count} expired pending registration(s):")
            for p in stale:
                self.stdout.write(f"  - {p.email} — {p.school_name} (expired {p.expires_at})")
            return

        emails = list(stale.values_list("email", flat=True))
        deleted, _ = stale.delete()

        logger.info(f"Cleaned up {deleted} expired pending registration(s): {emails}")
        self.stdout.write(
            self.style.SUCCESS(f"Deleted {deleted} expired pending registration(s).")
        )