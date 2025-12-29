# Changelog of rana-process-sdk


## 0.10 (2025-12-29)


- Small fix with reading process description


## 0.9 (2025-11-27)


- Actually the threedi API host setting.


## 0.8 (2025-11-21)


- Fix opted out parameter `log=False` in `set_progress` to be moved from runtime to context.


## 0.7 (2025-10-29)


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
