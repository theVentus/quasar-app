#include <metal_stdlib>
#include <SwiftUI/SwiftUI_Metal.h>
using namespace metal;

// Landing sky for a progressive book backdrop. Drawn per pixel: deep-space gradient, drifting nebula, twinkling
// two-layer starfield, a rising planet (continents, oceans, drifting clouds, terminator, atmosphere rim, night-side
// lights that grow with the story), and a sun cresting its limb with rays, an anamorphic streak and lens ghosts.
// Coordinates are in units of the view's height; `tilt` is a small device-motion parallax offset.

static float hash21(float2 p) {
    p = fract(p * float2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

static float vnoise(float2 p) {
    float2 i = floor(p);
    float2 f = fract(p);
    float a = hash21(i);
    float b = hash21(i + float2(1.0, 0.0));
    float c = hash21(i + float2(0.0, 1.0));
    float d = hash21(i + float2(1.0, 1.0));
    float2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

static float fbm(float2 p) {
    float v = 0.0;
    float a = 0.5;
    for (int i = 0; i < 5; i++) {
        v += a * vnoise(p);
        p = p * 2.03 + float2(1.7, 9.2);
        a *= 0.5;
    }
    return v;
}

[[ stitchable ]] half4 landingSky(float2 position, half4 color, float2 size, float time, float progress, float lattice, float2 tilt) {
    float2 uv = position / size.y;
    float aspect = size.x / size.y;

    // Space
    float3 col = mix(float3(0.012, 0.020, 0.030), float3(0.020, 0.055, 0.060), uv.y);

    // Nebula, slowly folding
    float2 q = uv * 2.0 + tilt * 0.02 + float2(time * 0.003, 0.0);
    float n = fbm(q + 1.3 * fbm(q * 1.6 + float2(time * 0.006, -time * 0.004)));
    col += float3(0.03, 0.20, 0.18) * pow(n, 3.2) * 1.4;
    col += float3(0.10, 0.12, 0.05) * pow(fbm(q * 0.7 + 7.0), 4.0) * 0.8;

    // Stars: a far fine layer and a nearer sparse one with more parallax
    for (int L = 0; L < 2; L++) {
        float scale = L == 0 ? 260.0 : 120.0;
        float2 g = (uv + tilt * (L == 0 ? 0.004 : 0.012)) * scale;
        float2 id = floor(g);
        float2 f = fract(g) - 0.5;
        float h = hash21(id + float(L) * 17.0);
        if (h > (L == 0 ? 0.982 : 0.990)) {
            float2 o = (float2(hash21(id + 3.1), hash21(id + 7.7)) - 0.5) * 0.6;
            float d = length(f - o);
            float tw = 0.55 + 0.45 * sin(time * (0.8 + h * 3.0) + h * 40.0);
            float3 tint = mix(float3(0.75, 0.9, 1.0), float3(1.0, 0.92, 0.8), hash21(id + 1.9));
            col += tint * smoothstep(L == 0 ? 0.07 : 0.10, 0.0, d) * tw * (L == 0 ? 0.8 : 1.4);
        }
    }

    // Planet rising from the lower right
    float R = 1.05;
    float2 pc = float2(aspect * 0.70, 1.0 + R * 0.58) + tilt * 0.018;
    float2 rel = uv - pc;
    float d = length(rel);

    // Sun cresting the upper-left limb; climbs with progress
    float2 limbDir = normalize(float2(-0.55, -1.0));
    float2 sun = pc + limbDir * (R + 0.015 + 0.05 * progress) + tilt * 0.01;
    float3 sunCol = float3(1.0, 0.93, 0.78);
    float3 L3 = normalize(float3(sun - pc, 0.35));

    if (d < R) {
        float z = sqrt(max(R * R - d * d, 0.0));
        float3 nrm = normalize(float3(rel, z));
        // Surface coordinates rotate slowly
        float2 tc = nrm.xy / (0.6 + nrm.z) * 1.6 + float2(time * 0.006, 0.0);
        float land = fbm(tc * 2.6 + 3.0);
        float3 ocean = mix(float3(0.02, 0.10, 0.12), float3(0.04, 0.22, 0.24), fbm(tc * 6.0));
        float3 green = mix(float3(0.10, 0.30, 0.10), float3(0.32, 0.55, 0.18), fbm(tc * 9.0 + 1.0));
        float3 surf = mix(ocean, green, smoothstep(0.48, 0.56, land));
        float clouds = smoothstep(0.55, 0.85, fbm(tc * 4.0 + float2(time * 0.012, time * 0.004)));
        surf = mix(surf, float3(0.92, 0.96, 0.95), clouds * 0.75);

        float diff = max(dot(nrm, L3), 0.0);
        float term = smoothstep(-0.05, 0.25, dot(nrm, L3));
        float3 lit = surf * (0.04 + 1.15 * diff);
        // Night-side lights grow as the story advances (a civilisation spreading)
        float cities = smoothstep(0.62, 0.70, fbm(tc * 22.0)) * smoothstep(0.5, 0.56, land);
        lit += float3(0.95, 0.75, 0.40) * cities * (1.0 - term) * smoothstep(0.15, 0.9, progress) * 0.9;
        // A web-like lattice across the surface late in the story
        float2 g = tc * 7.0;
        float lines = max(smoothstep(0.035, 0.0, abs(fract(g.x) - 0.5) - 0.46), smoothstep(0.035, 0.0, abs(fract(g.y + 0.5 * sin(g.x * 0.7)) - 0.5) - 0.46));
        lit += float3(0.75, 0.95, 0.85) * lines * lattice * 0.35 * (0.3 + 0.7 * term);
        // Limb darkening
        lit *= mix(0.55, 1.0, pow(nrm.z, 0.35));
        col = lit;
    }

    // Atmosphere rim, brightest toward the sun
    float rim = exp(-max(d - R, 0.0) * 38.0) * smoothstep(R - 0.03, R, d);
    float facing = 0.25 + 0.75 * max(dot(normalize(rel), normalize(sun - pc)), 0.0);
    col += float3(0.35, 0.85, 0.70) * rim * facing * 0.9;
    float inner = smoothstep(R - 0.06, R, d) * step(d, R);
    col += float3(0.25, 0.65, 0.55) * inner * facing * 0.4;

    // Sun: core, glow, rays, anamorphic streak
    float2 sd = uv - sun;
    float sl = length(sd);
    float core = exp(-sl * 55.0) * 2.2;
    float glow = exp(-sl * 6.0) * 0.55;
    float ang = atan2(sd.y, sd.x);
    float rays = pow(abs(sin(ang * 7.0 + time * 0.03)), 30.0) * exp(-sl * 4.5) * 0.35
               + pow(abs(sin(ang * 3.0 - time * 0.02 + 1.0)), 40.0) * exp(-sl * 3.0) * 0.2;
    float streak = exp(-abs(sd.y) * 120.0) * exp(-abs(sd.x) * 2.2) * 0.5;
    float occl = smoothstep(R - 0.01, R + 0.02, length(sun - pc)) * 0.6 + 0.4;
    col += sunCol * (core + glow + rays) * occl + float3(0.55, 0.85, 1.0) * streak * occl;

    // Lens ghosts along the line from the sun through the centre
    float2 centre = float2(aspect * 0.5, 0.5);
    for (int k = 1; k <= 4; k++) {
        float t = 0.35 * float(k);
        float2 gp = sun + (centre - sun) * (1.0 + t);
        float gr = 0.018 + 0.012 * float(k);
        float gd = length(uv - gp);
        float disc = smoothstep(gr, gr * 0.75, gd);
        float ring = smoothstep(gr * 1.08, gr, gd) - disc;
        float3 gc = k % 2 == 0 ? float3(0.35, 0.9, 0.85) : float3(0.6, 0.85, 1.0);
        col += gc * (disc * 0.05 + ring * 0.09) * occl;
    }

    // Gentle tone mapping
    col = col / (1.0 + col * 0.6);
    return half4(half3(col), 1.0);
}
