# Landing Profiles — pilot reference

## Airless-body descent (Mun, Minmus, Gilly, etc.)

### Suicide burn math

For a body with no atmosphere, the optimal powered descent is a **suicide burn**:
start the engine at the last possible moment to kill all velocity exactly at the surface.

**Key equation** (vertical descent approximation):

\[
t_{\text{burn}} = \frac{v_{\text{vertical}}}{g_0 \cdot \text{TWR} - g_{\text{body}}}
\]
\[
h_{\text{start}} = v_{\text{vertical}} \cdot t_{\text{burn}} - \frac{1}{2} (g_0 \cdot \text{TWR} - g_{\text{body}}) \cdot t_{\text{burn}}^2
\]

Where:
- \(v_{\text{vertical}}\) — current vertical speed (positive = moving away from surface)
- \(g_0 = 9.80665 \, \text{m/s}^2\)
- \(\text{TWR}\) — vessel thrust-to-weight ratio on the target body
- \(g_{\text{body}}\) — surface gravity of the body

**Practical approach** (used by `scripts/landing.py`):
1. From current orbit, compute surface-relative velocity at periapsis (≈ impact speed if no burn)
2. Using vessel TWR, compute burn start altitude and duration
3. Orient retrograde, throttle to maintain near-zero vertical velocity as altitude decreases
4. At < 5 m vertical speed and < 5 m altitude, cut throttle for touchdown

### Body reference data (airless)

| Body    | Surface g (m/s²) | Radius (km) | Typical suicide burn altitude |
|---------|------------------|-------------|------------------------------|
| Mun     | 1.63             | 200         | 5-10 km (from 100 km orbit)  |
| Minmus  | 0.491            | 60          | 2-5 km (from 60 km orbit)    |
| Gilly   | 0.049            | 13          | < 1 km                       |
| Bop     | 0.589            | 65          | 2-6 km                       |
| Pol     | 0.373            | 44          | 1-4 km                       |
| Eeloo   | 1.69             | 210         | 5-10 km                      |
| Moho    | 2.70             | 250         | 8-15 km                      |

---

## Atmospheric descent (Kerbin, Eve, Duna, Laythe, Jool)

### Reentry corridor

For bodies with atmospheres, use a **deorbit burn** to set periapsis in the upper
atmosphere, then let drag slow the vessel.

| Body    | Atmosphere height (km) | Deorbit Pe altitude (km) | Max temp (K) |
|---------|------------------------|--------------------------|-------------|
| Kerbin  | 70                     | 30-40 (shallow)          | 2000+       |
| Eve     | 90+                    | 55-70 (steep, thick)     | 3500+       |
| Duna    | 50                     | 10-20 (thin, shallow)    | 1250        |
| Laythe  | 50                     | 25-35                    | 2000+       |
| Jool    | 200                    | 120-150                  | 10000+      |

Shallow entry (higher Pe) = lower peak heating but more passes.  
Steep entry (lower Pe) = higher peak heating but single pass.

### Parachute deployment altitudes

Deploy parachutes only when aerodynamic pressure is sufficient AND speed is safe.

| Body    | Safe deploy Mach | Deploy altitude | Notes                           |
|---------|------------------|-----------------|----------------------------------|
| Kerbin  | < 0.5            | 2500-5000 m     | Full deploy at 1000 m            |
| Duna    | < 0.7            | 5000-10000 m    | Thin air; drogues first if heavy |
| Eve     | < 0.3            | 20000-35000 m   | Thick air; multiple chutes needed|
| Laythe  | < 0.6            | 5000-10000 m    | Similar to Kerbin                |

**Rule of thumb:** Kerbin parachutes open safely below 500 m/s and below 5000 m.
Drogue chutes can open at higher speeds (Mach 1+) and altitudes.

### Descent profile logic

```
1. Detect atmosphere (CelestialBody.atmosphere_depth > 0)
2. If atmosphere present:
   a. Deorbit burn: set Pe to upper atmosphere (e.g., 35 km for Kerbin)
   b. Coast to atmosphere entry (use warp-to.py)
   c. During aerobraking: maintain stability via SAS retrograde
   d. When speed < safe threshold: deploy drogue chutes (if available)
   e. When speed < terminal velocity: deploy main chutes
   f. If full chutes not enough: powered landing burn (Duna, Eve)
   g. Touchdown: throttle cutoff < 5 m/s vertical
3. If no atmosphere:
   a. Calculate suicide burn start altitude from current TWR and velocity
   b. Orient retrograde
   c. At start altitude: full throttle
   d. Modulate throttle to keep velocity vector toward retrograde
   e. At < 5 m: cut throttle, let legs absorb impact
```

### Hybrid profile (Duna)

Duna has a thin atmosphere — enough for parachutes to slow you significantly
but not enough for a full parachute landing.

```
1. Deorbit burn → Pe ~15 km Duna altitude
2. Aerobrake: parachutes at ~5-10 km (drogues earlier if heavy)
3. Chutes slow to ~50-100 m/s
4. At ~1000 m: ignite engines, throttle to reduce vertical to < 5 m/s
5. Cut at touchdown
```

---

## Landing site selection

### Runway landing (Kerbin)

KSC runway centre: lat = -0.097°, lon = -74.558° (default in-game).

For precision landing:
- Pass over KSC at ~10 km altitude
- Use aerobraking to slow
- Steer toward runway heading (180° from north)
- Touchdown at runway threshold (lights visible)

### Biome science landing

Target specific biomes for EVA reports / surface samples:

| Body    | Notable biomes                    |
|---------|-----------------------------------|
| Mun     | Highlands, Midlands, Lowlands, Craters, Polar |
| Minmus  | Flats (Great, Greater, Lesser), Highlands, Lowlands, Slopes, Polar |
| Kerbin  | Grasslands, Deserts, Tundra, Ice Caps, Oceans |
| Duna    | Midlands, Lowlands, Highlands, Polar, Craters |

### Flat terrain detection

Use kRPC `vessel.surface_height` at target coordinates to check terrain roughness.
Preferred landing zones: altitude variation < 5 m over 100 m radius.

---

## Abort handling

All landing scripts support:
- **Ctrl+C** or **Abort key**: immediately zero throttle, disengage autopilot, report abort
- **On abort**: vessel reverts to SAS retrograde (stability assist) for safe coast
- **On touchdown**: throttle zero, autopilot disengage, "Landed at [lat, lon]" report

---

## References

- kRPC API: `CelestialBody.atmosphere_depth`, `Vessel.flight()` for surface-relative velocity
- Stock KSP suicide burn calculator values from community (r/KerbalAcademy, KSP forums)
- Duna descent data from KSP Wiki (Duna atmosphere height = 50 km, density = 0.02 × Kerbin at sea level)
