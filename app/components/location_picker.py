"""Interactive OpenStreetMap location picker component."""

from __future__ import annotations

import base64

import httpx
import folium
import streamlit as st
from streamlit_folium import st_folium
from streamlit_searchbox import st_searchbox

from app.components.schema_registry import describe

_NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
_HEADERS = {"User-Agent": "open_datEAUbase/2.1.0 (water quality database)"}
_DEFAULT_LAT = 45.5017
_DEFAULT_LNG = -73.5673  # Montreal
_MAP_HEIGHT = 350

# Inlined as a data URI so the marker never depends on a CDN fetch
# (Leaflet's default icon is loaded from cdn.jsdelivr.net, which was failing
# intermittently on this network).
_PIN_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="25" height="41" viewBox="0 0 25 41">
<path d="M12.5 0C5.6 0 0 5.6 0 12.5c0 9.4 12.5 28.5 12.5 28.5s12.5-19.1 12.5-28.5C25 5.6 19.4 0 12.5 0z" fill="#2A81CB" stroke="#1c5a8e" stroke-width="1"/>
<circle cx="12.5" cy="12.5" r="5" fill="white"/>
</svg>"""
_PIN_ICON_URI = "data:image/svg+xml;base64," + base64.b64encode(_PIN_SVG.encode()).decode()


def _nominatim_search_raw(query: str) -> list[dict]:
    if not query or len(query) < 2:
        return []
    try:
        resp = httpx.get(
            f"{_NOMINATIM_BASE}/search",
            params={"q": query, "format": "json", "limit": 7, "addressdetails": 1},
            headers=_HEADERS,
            timeout=5.0,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return []


def _nominatim_reverse(lat: float, lng: float) -> dict:
    try:
        resp = httpx.get(
            f"{_NOMINATIM_BASE}/reverse",
            params={"lat": lat, "lon": lng, "format": "json"},
            headers=_HEADERS,
            timeout=5.0,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}


def _extract_address_fields(result: dict) -> tuple[str, str, str]:
    addr = result.get("address", {})
    city = (
        addr.get("city")
        or addr.get("town")
        or addr.get("village")
        or addr.get("municipality")
        or ""
    )
    province = addr.get("state") or addr.get("province") or addr.get("county") or ""
    country = addr.get("country") or ""
    return city, province, country


def _clear_location_state(key_prefix: str) -> None:
    """Remove all session state keys for a location picker instance."""
    for key in (
        f"{key_prefix}_lat_input",
        f"{key_prefix}_lng_input",
        f"{key_prefix}_city_input",
        f"{key_prefix}_province_input",
        f"{key_prefix}_country_input",
        f"{key_prefix}_last_click",
        f"{key_prefix}_last_selection",
        f"{key_prefix}_searchbox",
    ):
        st.session_state.pop(key, None)


def render_location_picker(
    lat: float | None = None,
    lng: float | None = None,
    city: str | None = None,
    province: str | None = None,
    country: str | None = None,
    key_prefix: str = "loc",
) -> dict:
    """Render an OSM location picker with address autocomplete and reverse geocoding.

    Returns dict with keys: lat_wgs84, long_wgs84, city, province, country.
    """
    k_lat = f"{key_prefix}_lat_input"
    k_lng = f"{key_prefix}_lng_input"
    k_city = f"{key_prefix}_city_input"
    k_province = f"{key_prefix}_province_input"
    k_country = f"{key_prefix}_country_input"
    k_last_click = f"{key_prefix}_last_click"
    k_last_selection = f"{key_prefix}_last_selection"

    # Initialise once per form open
    if k_lat not in st.session_state:
        st.session_state[k_lat] = float(lat) if lat is not None else _DEFAULT_LAT
        st.session_state[k_lng] = float(lng) if lng is not None else _DEFAULT_LNG
        st.session_state[k_city] = city or ""
        st.session_state[k_province] = province or ""
        st.session_state[k_country] = country or ""
        st.session_state[k_last_click] = None
        st.session_state[k_last_selection] = None

    # --- Address autocomplete ---
    # Return (display_label, nominatim_result_dict) tuples so st_searchbox
    # hands us the full result dict on selection — no cache needed.
    def _search(query: str) -> list[tuple[str, dict]]:
        results = _nominatim_search_raw(query)
        return [
            (r["display_name"], r)
            for r in results
            if r.get("display_name")
        ]

    selected: dict | None = st_searchbox(
        _search,
        key=f"{key_prefix}_searchbox",
        placeholder="Search address or place name...",
        label="Search address",
        clear_on_submit=False,
    )

    # Process a new selection (guard against re-processing the same result)
    if isinstance(selected, dict):
        sel_coords = (round(float(selected["lat"]), 6), round(float(selected["lon"]), 6))
        if sel_coords != st.session_state[k_last_selection]:
            st.session_state[k_last_selection] = sel_coords
            st.session_state[k_lat] = sel_coords[0]
            st.session_state[k_lng] = sel_coords[1]
            city_r, prov_r, country_r = _extract_address_fields(selected)
            st.session_state[k_city] = city_r
            st.session_state[k_province] = prov_r
            st.session_state[k_country] = country_r
            st.session_state[k_last_click] = None

    # --- Map ---
    center_lat = st.session_state[k_lat]
    center_lng = st.session_state[k_lng]

    m = folium.Map(location=[center_lat, center_lng], zoom_start=12)
    folium.Marker(
        [center_lat, center_lng],
        tooltip=f"{center_lat:.6f}, {center_lng:.6f}",
        icon=folium.CustomIcon(_PIN_ICON_URI, icon_size=(25, 41), icon_anchor=(12, 41)),
    ).add_to(m)

    # Key encodes coordinates so the component re-mounts (showing new marker)
    # whenever lat/lng changes, instead of keeping stale browser-side state.
    map_key = f"{key_prefix}_map_{round(center_lat, 5)}_{round(center_lng, 5)}"

    map_data = st_folium(
        m,
        height=_MAP_HEIGHT,
        use_container_width=True,
        key=map_key,
        returned_objects=["last_clicked"],
    )

    # --- Map click handler ---
    if map_data and map_data.get("last_clicked"):
        clicked = map_data["last_clicked"]
        clicked_lat = round(float(clicked["lat"]), 6)
        clicked_lng = round(float(clicked["lng"]), 6)
        if (clicked_lat, clicked_lng) != st.session_state[k_last_click]:
            st.session_state[k_last_click] = (clicked_lat, clicked_lng)
            st.session_state[k_lat] = clicked_lat
            st.session_state[k_lng] = clicked_lng
            result = _nominatim_reverse(clicked_lat, clicked_lng)
            if result:
                city_r, prov_r, country_r = _extract_address_fields(result)
                st.session_state[k_city] = city_r
                st.session_state[k_province] = prov_r
                st.session_state[k_country] = country_r
            st.rerun()

    st.caption("Click on the map to set coordinates, or search by address above.")

    # --- Coordinate inputs ---
    col_lat, col_lng = st.columns(2)
    with col_lat:
        st.number_input(
            "Latitude",
            min_value=-90.0,
            max_value=90.0,
            format="%.6f",
            step=0.000001,
            key=k_lat,
            help=describe("Site", "latitude_wgs84"),
        )
    with col_lng:
        st.number_input(
            "Longitude",
            min_value=-180.0,
            max_value=180.0,
            format="%.6f",
            step=0.000001,
            key=k_lng,
            help=describe("Site", "longitude_wgs84"),
        )

    # --- Address text fields ---
    col_c, col_p, col_co = st.columns(3)
    with col_c:
        st.text_input("City", key=k_city, help=describe("Site", "city"))
    with col_p:
        st.text_input(
            "Province / State", key=k_province, help=describe("Site", "province")
        )
    with col_co:
        st.text_input("Country", key=k_country, help=describe("Site", "country"))

    return {
        "lat_wgs84": st.session_state[k_lat],
        "long_wgs84": st.session_state[k_lng],
        "city": st.session_state[k_city] or None,
        "province": st.session_state[k_province] or None,
        "country": st.session_state[k_country] or None,
    }
