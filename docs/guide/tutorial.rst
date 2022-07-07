========
Tutorial
========

Migrating from Django Signals
-----------------------------

Let's you have models and signals like this::

    # events.models.py

    class Event(models.Model):
        name = models.CharField(max_length=255)
        starts_at = models.DateTimeField()
        duration = models.DurationField(default=timedelta(hours=1))


    @receiver(pre_save, sender=Event)
    def event_pre_save(sender, instance, **kwargs):
        if not instance.id:
            return

        old_instance = Event.objects.get(id=instance.id)
        if old_instance.starts_at != instance.starts_at or old_instance.duration !=  instance.duration:
            event_tasks.resync_event_calendars.delay(event_id=instance.id)


    class Enrollment(models.Model):

        PARTICIPANT = 'participant'
        SPEETCHER = 'speetcher'
        ORGANIZER = 'organizer'
        CO_ORGANIZER = 'co_organizer'

        ROLE_CHOICES = [
            (PARTICIPANT, 'Participant'),
            (SPEETCHER, 'Speetcher'),
            (ORGANIZER, 'Organizer'),
            (CO_ORGANIZER, 'Co-Organizer'),
        ]

        role = models.CharField(ax_length=255, choices=ROLE_CHOICES)

        user = models.ForeignKey("users.User", models.CASCADE, related_name="enrollments")
        event = models.ForeignKey("events.Event", models.CASCADE, related_name="enrollments")


    @receiver(post_delete, sender=Enrollment)
    def enrollment_post_save(sender, instance, **kwargs):
        event_tasks.remove_enrollment_calendar.delay(enrollment_id=instance.id)


Transforming it to a Watcher::

    # events.watchers.py

    from django_watchers.mixins import UpdateWatcherMixin, DeleteWatcherMixin

    EventWatcher(UpdateWatcherMixin):
        @classmethod
        def pre_update(cls, target, meta_params):
            source = meta_params.get('source')

            if source == 'queryset':
                operation_params = meta_params.get('operation_params')
                resync = 'starts_at' in operation_params or 'duration' in operation_params
            else:
                old_instance = target.first()
                instance = meta_params.get('instance_ref')
                resync = old_instance.starts_at != instance.starts_at or old_instance.duration !=  instance.duration:

            if resync:
                event_tasks.resync_event_calendars.delay(event_ids=target.values_list('id'))


    EnrollmentWatcher(DeleteWatcherMixin):
        @classmethod
        def post_delete(cls, target):
            event_tasks.remove_enrollment_calendar.delay(enrollment_ids=[enrollment.id for enrollment in target])

    # events.models.py

    from django_watcher.decorators import watched

    from .watchers import EventWatcher, EnrollmentWatcher


    @watched(EventWatcher)
    class Event(models.Model):
        name = models.CharField(max_length=255)
        starts_at = models.DateTimeField()
        duration = models.DurationField(default=timedelta(hours=1))


    @watched(EnrollmentWatcher)
    class Enrollment(models.Model):

        PARTICIPANT = 'participant'
        SPEETCHER = 'speetcher'
        ORGANIZER = 'organizer'
        CO_ORGANIZER = 'co_organizer'

        ROLE_CHOICES = [
            (PARTICIPANT, 'Participant'),
            (SPEETCHER, 'Speetcher'),
            (ORGANIZER, 'Organizer'),
            (CO_ORGANIZER, 'Co-Organizer'),
        ]

        role = models.CharField(ax_length=255, choices=ROLE_CHOICES)

        user = models.ForeignKey("users.User", models.CASCADE, related_name="enrollments")
        event = models.ForeignKey("events.Event", models.CASCADE, related_name="enrollments")


