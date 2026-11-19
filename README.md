# Bincom Elections — clearer UI (Django + SQLite + Tailwind)

This is the user's original Django project, updated with a cleaner, responsive user interface. Existing election data and the original Bincom tables are preserved. It still implements the three Bincom assessment questions:

- **Question 1:** Browse and search polling units, then open results for a selected unit.
- **Question 2:** Select an LGA and calculate party totals from its polling-unit results (not `announced_lga_results`).
- **Question 3:** Register a new polling unit with a score for every party, in one atomic transaction.

## Start the project

Extract the ZIP and open the `bincom_service` directory (the one containing `manage.py`).

If you have an existing virtual environment, activate it. Otherwise:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Then run:

```bash
python manage.py check
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. The app uses the supplied `bincom_test.sqlite3` file by default, set in `config/settings.py`.

## Pages

| Page | URL |
| --- | --- |
| Overview | `/` |
| Find polling units | `/election/poll-units/` |
| Polling unit results | `/election/poll-unit/8/` (or any actual unit unique ID) |
| LGA results | `/election/lga-result/` |
| Register new results | `/election/create-poll-result/` |

## Tailwind CSS CDN

`templates/base.html` loads the official Tailwind v4 Play CDN, shared by **all** pages:

```html
<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
```

This requires an internet connection to load the styles and is intended for **development/assessment demos**, not a production deployment. No Node/npm setup required.

## Important database details

- The original source schema uses `PollingUnit.lga_id = Lga.lga_id`, **not** `Lga.uniqueid`.
- Unit results link `AnnouncedPuResult.polling_unit_uniqueid` (text) to `PollingUnit.uniqueid` (integer).
- The form shows `LABOUR` using the `Party` table, and saves `LABO` to `announced_pu_results` for compatibility. Original data is unchanged.
- The source's historical zero-date records are mapped to `CharField`. The included SQLite file has its date columns declared `TEXT`.
- Bincom data models are `managed = False`, since their tables already exist.
- `django.contrib` migration warnings are unrelated to the imported results tables. Make a database backup before applying any migrations if you plan to use auth/admin sessions.

## Changes made for usability

- Real homepage with summary counts and quick links.
- Searchable polling-unit directory; filter by LGA and show units with or without recorded votes.
- Clear result totals and empty states, including for LGAs without results.
- Responsive navigation and pages, consistent spacing, clearer form labels and inline errors.
- Live total-votes counter as the user types, and the ward list follows the chosen LGA.
- New results still use atomic insertion and redirect to the saved polling unit.

`venv/`, `__pycache__/`, and `.DS_Store` are intentionally excluded.
