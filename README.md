# Cornell CVM Events for Appspace + BrightSign

This package replaces the Localist JavaScript widget with a static HTML page that BrightSign can display reliably.

## Files included

- `generate_events.py`
- `.github/workflows/update-events.yml`
- `index.html`

## Installation

1. Upload all files and folders to the root of your GitHub repository.
2. Commit the files to the `master` branch.
3. Open **Settings → Actions → General**.
4. Under **Workflow permissions**, select **Read and write permissions**.
5. Click **Save**.
6. Open the **Actions** tab.
7. Select **Update Cornell Events**.
8. Click **Run workflow** and run it on `master`.
9. Wait for the workflow to finish with a green check.
10. Confirm that `index.html` now contains the generated event cards.

## GitHub Pages

Under **Settings → Pages**, use:

- Source: `Deploy from a branch`
- Branch: `master`
- Folder: `/ (root)`

## Appspace URL

Use:

https://tjp58.github.io/cvm-events/index.html?v=1

After changing the generated files, increment the number after `v=` to force a fresh load.

## Schedule

The workflow updates the page once per hour at 15 minutes past the hour.
