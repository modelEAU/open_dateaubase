# Add a Site and Field System

Before you can create a campaign or ingest data, you need a **Site** (where measurements happen) and a **Field System** (the equipment that produces them).

This how-to guide shows the fastest way to set both up in the web app.

## Add a site

1. Go to **Workflows → 1. New Site Wizard**.
2. Enter the site name and select a site kind.
3. Add at least one sampling location with a name and optional coordinates.
4. Save.

## Add a field system

1. Go to **Workflows → 2. New Field System Wizard**.
2. Create or select an **Equipment Model** (manufacturer + model name).
3. Create an **Equipment** instance using a unique serial number or asset tag.
4. Record the installation at the sampling location you just created.
5. Save.

## Verify

- **Entities → Sites** should list the new site.
- **Entities → Equipment** should list the new equipment instance.
- The site and equipment are now available in the Campaign Wizard.

## Next step

Create your first campaign: [Your First Campaign](../tutorials/first_campaign.md).
