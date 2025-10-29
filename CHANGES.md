# Changelog of rana-process-sdk


## 0.7 (unreleased)


- Also emit an INFO-level log when `RanaContext.set_progress` is called. This
  can be opted out from by using the parameter `log=False`.


## 0.6 (2025-10-02)


- Extend the `get_dataset` to also include WMS and ATOM Service details.


## 0.5 (2025-09-24)


- Added `data_type_override` to `RanaContext.set_output` and made arguments keyword-only.


## 0.4 (2025-09-22)


- Added Sentry logging for crashed processes.


## 0.3 (2025-09-18)


- Adjust local test default yaml path to `local_test.conf`


## 0.2 (2025-09-16)


- Added `context.get_dataset`.

- Add support for retrieving WCS and WFS links for Rana datasets.

- Change the test settings model.


## 0.1 (2025-09-16)

- Code overhaul from Rana main repository, renaming `rana_sdk` to `rana_process_sdk`.

- Minor change in test setup to be able to run the tests without `settings.yaml`.

- Initial project structure created with cookiecutter and
  [cookiecutter-python-template](https://github.com/nens/cookiecutter-python-template).
