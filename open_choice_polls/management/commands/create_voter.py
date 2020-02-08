import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from open_choice_polls import settings
from open_choice_polls.models import Voter
from django.db.utils import IntegrityError


class Command(BaseCommand):
    help = 'Create some voters'

    def add_arguments(self, parser):
        parser.add_argument('--amount', type=int, default=1, help='Amount to create')

    def handle(self, *args, **options):
        amount = options.get('amount')

        prefix = settings.OPEN_CHOICE_POLLS_VOTER_PREFIX

        ids_rand = random.sample(range(settings.OPEN_CHOICE_POLLS_VOTER_RANGE_START,
                                       settings.OPEN_CHOICE_POLLS_VOTER_RANGE_END), amount)

        for i in ids_rand:
            # Create user and save to the database
            voter_username = '{}{}'.format(prefix, str(i).zfill(3))
            try:
                enrollment_code = Voter.create_enrollment_code()
                user = User.objects.create_user(voter_username, password=enrollment_code)

                user.is_staff = True  # ToDo(frennkie) remove this..!

                user.voter.is_voter = True
                user.voter.enrollment_code = enrollment_code
                user.save()

                self.stdout.write(self.style.SUCCESS('Successfully created 1 voter: {}'.format(voter_username)))
            except IntegrityError:
                self.stdout.write(self.style.WARNING('Failed to create 1 voter: {}'.format(voter_username)))
