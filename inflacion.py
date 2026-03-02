import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import numpy as np
from datetime import date

# ══════════════════════════════════════════════════════════
# PRESIDENTES — colores por partido político
# ══════════════════════════════════════════════════════════
PRESIDENTES = [
    {
        "nombre": "Macri",
        "partido": "PRO",
        "color": "#F59E0B",        # amarillo dorado
        "inicio": "2015-12-10",
        "fin":    "2019-12-10",
    },
    {
        "nombre": "Alberto F.",
        "partido": "Frente de Todos",
        "color": "#3B82F6",        # azul peronista
        "inicio": "2019-12-10",
        "fin":    "2023-12-10",
    },
    {
        "nombre": "Milei",
        "partido": "La Libertad Avanza",
        "color": "#A855F7",        # violeta libertario
        "inicio": "2023-12-10",
        "fin":    str(date.today()),
    },
]

# ══════════════════════════════════════════════════════════
# DESCARGA — siempre hasta hoy automáticamente
# ══════════════════════════════════════════════════════════
hoy = date.today().strftime("%Y-%m-%d")
print(f"🔄 Bajando datos hasta {hoy}...")

respuesta = requests.get(
    "https://apis.datos.gob.ar/series/api/series/",
    params={
        "ids": "103.1_I2N_2016_M_19",
        "format": "json",
        "limit": 200,
        "start_date": "2016-01-01",
        "end_date": hoy,
        "representation_mode": "percent_change"
    }
)

if respuesta.status_code != 200:
    print(f"❌ Error HTTP: {respuesta.status_code}")
    exit()

datos = respuesta.json()
if "data" not in datos:
    print("❌ Sin clave 'data':", datos)
    exit()

df = pd.DataFrame(datos["data"], columns=["fecha", "inflacion"])
df["fecha"]     = pd.to_datetime(df["fecha"])
df["inflacion"] = pd.to_numeric(df["inflacion"]) * 100

# Variación mes a mes (cuánto SUBIÓ o BAJÓ la inflación respecto al mes anterior)
df["delta"] = df["inflacion"].diff()

ultimo_dato = df["fecha"].max().strftime("%B %Y")
print(f"✅ {len(df)} meses cargados. Último dato: {ultimo_dato}\n")

# ══════════════════════════════════════════════════════════
# ASIGNAR PRESIDENTE A CADA MES
# ══════════════════════════════════════════════════════════
def presidente_del_mes(fecha):
    for p in PRESIDENTES:
        if pd.to_datetime(p["inicio"]) <= fecha <= pd.to_datetime(p["fin"]):
            return p["nombre"]
    return None

df["presidente"] = df["fecha"].apply(presidente_del_mes)

# ══════════════════════════════════════════════════════════
# ESTADÍSTICAS POR PRESIDENTE
# ══════════════════════════════════════════════════════════
stats = {}
for p in PRESIDENTES:
    seg = df[df["presidente"] == p["nombre"]].copy()
    if seg.empty:
        continue

    # Inflación acumulada real = producto de (1 + r/100)
    acumulada = (np.prod(1 + seg["inflacion"] / 100) - 1) * 100

    stats[p["nombre"]] = {
        "color":         p["color"],
        "partido":       p["partido"],
        "meses":         len(seg),
        "promedio":      seg["inflacion"].mean(),
        "max_mes":       seg.loc[seg["inflacion"].idxmax()],
        "min_mes":       seg.loc[seg["inflacion"].idxmin()],
        "mayor_subida":  seg.loc[seg["delta"].idxmax()],   # mes que mas subio la inflacion
        "mayor_bajada":  seg.loc[seg["delta"].idxmin()],   # mes que mas bajo la inflacion
        "acumulada":     acumulada,
        "nominal":       seg["inflacion"].sum(),           # suma simple
    }

# ══════════════════════════════════════════════════════════
# GRÁFICO PRINCIPAL
# ══════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(20, 9))
fig.patch.set_facecolor("#0F0F0F")
ax.set_facecolor("#0F0F0F")

# Dibujar segmento de línea por presidente (color cambia)
for p in PRESIDENTES:
    seg = df[df["presidente"] == p["nombre"]]
    if seg.empty:
        continue

    # Unir con el último punto del segmento anterior para que no haya gap
    idx_start = seg.index[0]
    if idx_start > 0:
        punto_anterior = df.loc[[idx_start - 1]]
        seg = pd.concat([punto_anterior, seg])

    ax.plot(seg["fecha"], seg["inflacion"],
            color=p["color"], linewidth=2.5, zorder=4)
    ax.fill_between(seg["fecha"], seg["inflacion"],
                    alpha=0.07, color=p["color"], zorder=2)

    # Nombre del presidente en el centro del segmento
    seg_real = df[df["presidente"] == p["nombre"]]
    centro_fecha = seg_real["fecha"].iloc[len(seg_real)//2]
    ax.text(centro_fecha, -1.8, p["nombre"],
            ha="center", fontsize=9, color=p["color"],
            fontweight="bold", alpha=0.9)

# Línea separadora entre presidentes
for p in PRESIDENTES[1:]:
    ax.axvline(pd.to_datetime(p["inicio"]),
               color="white", linewidth=0.8, linestyle="--", alpha=0.3, zorder=5)

# ── TOP 3 PICOS MÁS ALTOS ──
top3_altos = df.nlargest(3, "inflacion")
for _, row in top3_altos.iterrows():
    color_p = next((p["color"] for p in PRESIDENTES if p["nombre"] == row["presidente"]), "red")
    ax.annotate(
        f'+{row["inflacion"]:.1f}%\n{row["fecha"].strftime("%b %Y")}',
        xy=(row["fecha"], row["inflacion"]),
        xytext=(0, 16), textcoords="offset points",
        ha="center", fontsize=8, color=color_p, fontweight="bold",
        arrowprops=dict(arrowstyle="->", color=color_p, lw=1.3),
        zorder=6
    )

# ── TOP 3 MESES CON MAYOR SUBIDA de un mes al siguiente ──
top3_subidas = df.nlargest(3, "delta")
for _, row in top3_subidas.iterrows():
    ax.annotate(
        f'▲{row["delta"]:.1f}pp\n{row["fecha"].strftime("%b %Y")}',
        xy=(row["fecha"], row["inflacion"]),
        xytext=(18, 6), textcoords="offset points",
        fontsize=7.5, color="#F97316",
        arrowprops=dict(arrowstyle="-", color="#F97316", lw=0.8),
        zorder=6
    )

# ── TOP 3 MESES CON MAYOR BAJADA de un mes al siguiente ──
top3_bajadas = df.nsmallest(3, "delta")
for _, row in top3_bajadas.iterrows():
    ax.annotate(
        f'▼{abs(row["delta"]):.1f}pp\n{row["fecha"].strftime("%b %Y")}',
        xy=(row["fecha"], row["inflacion"]),
        xytext=(18, -18), textcoords="offset points",
        fontsize=7.5, color="#34D399",
        arrowprops=dict(arrowstyle="-", color="#34D399", lw=0.8),
        zorder=6
    )

# ── PROYECCIÓN 12 meses ──
ultimos_6_prom = df.tail(6)["inflacion"].mean()
ultima_fecha   = df["fecha"].max()
fechas_proy    = pd.date_range(start=ultima_fecha, periods=13, freq="MS")[1:]
ax.plot(fechas_proy, [ultimos_6_prom]*12,
        color="white", linewidth=1.5, linestyle=":", alpha=0.5, zorder=3)
ax.text(fechas_proy[-1], ultimos_6_prom + 0.4,
        f"Proy. {ultimos_6_prom:.1f}%/mes",
        color="white", fontsize=7.5, alpha=0.7)

# ── FORMATO EJE ──
ax.tick_params(colors="white", labelsize=8)
for spine in ax.spines.values():
    spine.set_edgecolor("#333")
ax.xaxis.label.set_color("white")
ax.yaxis.label.set_color("white")
ax.set_xlabel("Fecha", labelpad=8)
ax.set_ylabel("Inflacion mensual (%)", labelpad=8)
ax.set_title(f"Inflacion Mensual Argentina — IKE 34   |   Datos hasta {ultimo_dato}",
             fontsize=14, color="white", pad=14)
ax.grid(True, alpha=0.12, color="white")
ax.set_ylim(bottom=-3)

# ── LEYENDA ──
leyenda = [mpatches.Patch(color=p["color"], label=f'{p["nombre"]}  ({p["partido"]})', alpha=0.8)
           for p in PRESIDENTES]
leyenda += [
    mlines.Line2D([], [], color="#F97316", label="▲ Mayor subida mensual"),
    mlines.Line2D([], [], color="#34D399", label="▼ Mayor bajada mensual"),
    mlines.Line2D([], [], color="white",   label="Proyeccion", linestyle=":"),
]
ax.legend(handles=leyenda, loc="upper left", fontsize=8,
          facecolor="#1a1a1a", edgecolor="#444", labelcolor="white")

plt.tight_layout()
plt.savefig("inflacion_ike34.png", dpi=150, facecolor=fig.get_facecolor())
plt.show()

# ══════════════════════════════════════════════════════════
# REPORTE FINAL EN CONSOLA
# ══════════════════════════════════════════════════════════
separador = "═" * 60

print(f"\n{separador}")
print("  REPORTE DE INFLACION POR GOBIERNO — IKE 34")
print(separador)

for nombre, s in stats.items():
    print(f"\n  {nombre.upper()}  ({s['partido']})  — {s['meses']} meses")
    print(f"  {'─'*46}")
    print(f"  Inflacion acumulada REAL  : {s['acumulada']:>8.1f}%")
    print(f"  Inflacion nominal (suma)  : {s['nominal']:>8.1f}%")
    print(f"  Promedio mensual          : {s['promedio']:>8.2f}%")
    print(f"  Peor mes                  : {s['max_mes']['inflacion']:.1f}%  ({s['max_mes']['fecha'].strftime('%b %Y')})")
    print(f"  Mejor mes                 : {s['min_mes']['inflacion']:.1f}%  ({s['min_mes']['fecha'].strftime('%b %Y')})")
    print(f"  Mayor subida mensual      : +{s['mayor_subida']['delta']:.1f}pp  ({s['mayor_subida']['fecha'].strftime('%b %Y')})")
    print(f"  Mayor bajada mensual      : {s['mayor_bajada']['delta']:.1f}pp  ({s['mayor_bajada']['fecha'].strftime('%b %Y')})")

# ── RANKINGS FINALES ──
print(f"\n{separador}")
print("  RANKINGS FINALES")
print(separador)

mas_acum   = max(stats, key=lambda x: stats[x]["acumulada"])
menos_acum = min(stats, key=lambda x: stats[x]["acumulada"])
mas_prom   = max(stats, key=lambda x: stats[x]["promedio"])
menos_prom = min(stats, key=lambda x: stats[x]["promedio"])
mas_bajo   = min(stats, key=lambda x: stats[x]["mayor_bajada"]["delta"])

print(f"\n  🔴 Mas inflacion acumulada REAL : {mas_acum}  ({stats[mas_acum]['acumulada']:.0f}%)")
print(f"  🟢 Menos inflacion acumulada    : {menos_acum}  ({stats[menos_acum]['acumulada']:.0f}%)")
print(f"  🔴 Mayor promedio mensual       : {mas_prom}  ({stats[mas_prom]['promedio']:.2f}%/mes)")
print(f"  🟢 Menor promedio mensual       : {menos_prom}  ({stats[menos_prom]['promedio']:.2f}%/mes)")
print(f"  🟢 Mayor bajada en un mes       : {mas_bajo}  ({stats[mas_bajo]['mayor_bajada']['delta']:.1f}pp en {stats[mas_bajo]['mayor_bajada']['fecha'].strftime('%b %Y')})")

# ── CALCULADORA ──
print(f"\n{separador}")
print("  CALCULADORA DE PROYECCION")
print(separador)
try:
    monto = float(input("\n  Monto en pesos: $"))
    meses = int(input("  Proyectar cuantos meses: "))
    tasa  = float(input(f"  Tasa mensual (Enter = {ultimos_6_prom:.2f}% promedio reciente): ") or ultimos_6_prom)

    print(f"\n  Con {tasa:.2f}% mensual:\n")
    print(f"  {'Mes':<6} {'Inflacion acum':>16}   {'Valor $':>14}")
    print(f"  {'─'*40}")
    valor = monto
    for mes in range(1, meses + 1):
        valor *= (1 + tasa / 100)
        acum = ((valor / monto) - 1) * 100
        print(f"  {mes:<6} {acum:>14.1f}%   ${valor:>12,.0f}")

    perdida = (1 - monto / valor) * 100
    print(f"\n  Tu ${ monto:,.0f} de hoy se convierte en ${valor:,.0f}")
    print(f"  Perdida de poder adquisitivo: {perdida:.1f}%")
except:
    print("  Calculadora omitida.")

print(f"\n{separador}")
print("  Grafico guardado: inflacion_ike34.png")
print(separador)