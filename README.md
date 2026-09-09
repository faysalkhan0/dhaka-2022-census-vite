# Dhaka 2022 Census Explorer — Vite + Mapbox

Interactive 2D Web GIS for the Dhaka Population and Housing Census 2022.

## You do not need to code

1. Upload this whole folder to GitHub.
2. Create a `.env.local` file locally (or configure the same environment variable in your hosting service):
   `VITE_MAPBOX_TOKEN=pk_your_public_token`
3. Run `npm install` once, then `npm run dev`.
4. For production: `npm run build`.

The browser frontend is intentionally small and uses Vite + Mapbox GL JS. Python is used for the reproducible census/GIS data-preparation pipeline in `scripts/build_data.py`.

## Map behavior

- 2D only.
- Satellite and dark basemap.
- Census choropleth and boundary-only mode.
- Hover: compact floating card with three values.
- Click: right sidebar with all available census data for that area, shown as headings and value rows — not an HTML table.
- Drill-down follows the Dhaka hierarchy: District → City Corporation / Upazila → Ward / Union / Paurashava → Mauza/Village.
- City thana geometry is retained as support data but is not a clickable navigation level.
- Upazila geometry is included and loaded on demand.

## Data

The authoritative census source is the supplied Dhaka 2022 census Excel workbook. Values are preserved; the web files are optimized representations for visualization.

The five census records with no matching polygon in the final GIS source remain in the census data and are not substituted with unrelated geometry.

## Rebuild web data

The Python script expects the three source files in `source/`:

- `Dhaka_2022_census_data.xlsx`
- `Dhaka_2022_Census_MapData.csv`
- `Dhaka_2022_Census_MapGeometry_final.gpkg`

Run:

```bash
python scripts/build_data.py
```

## Mapbox token

Use a **public** Mapbox token (`pk...`) restricted to your GitHub Pages/custom-domain URL. Do not commit a secret token.

## GitHub Pages deployment

The repository includes a GitHub Actions workflow. After uploading/pushing it to the `main` branch:

1. In GitHub, open **Settings → Secrets and variables → Actions**.
2. Add repository secret `VITE_MAPBOX_TOKEN` with your Mapbox public `pk...` token.
3. Open **Settings → Pages** and choose **GitHub Actions** as the source.
4. Push to `main`; the workflow builds and deploys the site.

You do not need to edit the JavaScript application code.
