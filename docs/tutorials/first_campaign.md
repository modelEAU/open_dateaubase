# Your First Campaign

This tutorial walks you through the full campaign setup in the web app: creating a site, registering a field system, and using the Campaign Wizard to tie everything together.

By the end you will have a campaign with equipment deployments and sampling locations, ready to receive sensor or lab data.

## What you need

- A running open_datEAUbase stack (`docker compose up -d` is enough).
- Login credentials for the Streamlit app.

## Steps

### 1. Create a site

Go to **Workflows → 1. New Site Wizard** and enter at least the site name and type. Add one or more sampling locations while you are there — the campaign wizard will need them.

### 2. Register a field system

Go to **Workflows → 2. New Field System Wizard**. This creates the equipment model and equipment instance that the campaign will deploy.

### 3. Run the Campaign Wizard

Go to **Workflows → 3. New Campaign Wizard**. The wizard checks that you already have sites and equipment, then guides you through:

- Campaign details (name, type, dates, description).
- Site and sampling locations.
- Equipment deployments.
- Review and create.

### 4. Verify the campaign

Go to **Entities → Campaigns**. Your new campaign appears in the table. Click it to see deployments, locations, and linked data.

## Next steps

- [Lab Panels and Results](lab_panel_and_results.md) — configure a panel of analytes and report lab results against this campaign.
- [Explore Your Data](explore_your_data.md) — plot the data you just set up.
