# Django Data Watcher
## _Django models/data operations observer_


Django Data Watcher is a library that will make easier to create/mantain side-effects
of data operations in your django models.

- Write once
- Have visibility
- Acts always on querysets, avoinding bottlenecks

## Features

- [x] Override save for models
- [x] Limit the number of functions on watcher eg. instead of save, _save and watched_save have only _save and _watched_save or maybe just one of those
- [x] Make watched_operations restrict
- [x] Delete and Create Mixins
- [x] Update and Save Mixins
- [x] Take a look into _default_manager and _base_manager (Create specific test cases)
- [ ] Packaging
- [ ] Test
- [x] Remove return from save operations
- [ ] Limit the watched operations? (only delete, create, update, save)
- [ ] Model.objects.create() calls instance.save().
  - [ ] Do we want to support possible overrides of qs.create() that don't call instance.save()?
  - [x] queryset UNWATCHED_create needs to call UNWATCHED_save of instance
- [ ] Application Example also comparing with Django signals
- [ ] Implement for bulk operations on qs (bulk_create and bulk_update)
- [ ] Docs
- [ ] Talk
