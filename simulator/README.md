# E1 · Trazada — Simulador de línea de carrera

Prototipo web jugable para **aprender la trazada** de un circuito de boyas tipo
E1 Series. El móvil es el volante: inclínalo para girar. El barco avanza solo y,
si giras demasiado fuerte para tu velocidad, **escurre y pierde tiempo** — la
línea suave es la rápida.

## Cómo probarlo

- **iPhone:** abre `simulator/index.html`, pulsa **Empezar** y permite el acceso
  a movimiento. Calibra el cero sujetando el móvil como vas a jugar.
- **Escritorio:** ábrelo en el navegador y usa las flechas **← →** para girar.

Sirviéndolo en local:

```bash
cd simulator && python3 -m http.server 8000
# luego abre http://<ip-del-pc>:8000 desde el iPhone (misma red)
```

> iOS solo entrega el sensor de orientación por **HTTPS** o `localhost`. Para
> jugar desde el teléfono usa un túnel (ngrok/Cloudflare) o despliega el archivo
> en cualquier hosting estático.

## El modelo físico (el corazón)

Todo sale de una sola regla. Cada frame:

```
ω      = K_STEER · inclinación        // velocidad de giro (volante)
a_lat  = v · ω                        // aceleración lateral
scrub  = max(0, |a_lat| − A_MAX)      // cuánto te pasas del agarre
v     += (THRUST − DRAG·v² − SCRUB_K·scrub) · dt
```

No hay tabla de "grados → frenada": la penalización **emerge** de superar el
límite de agarre `A_MAX`. Por eso un giro brusco a baja velocidad es gratis y el
mismo giro a tope te frena. La trazada ideal (entrada/apex/salida amplios)
aparece sola porque minimiza la curvatura y mantiene `a_lat` bajo el límite.

### Mandos de ajuste (panel ⚙︎)

| Variable  | Qué controla |
|-----------|--------------|
| `A_MAX`   | Agarre lateral del casco. El número más importante. |
| `SCRUB_K` | Dureza del frenazo al sobre-girar. |
| `THRUST`  | Empuje del motor (recuperación en recta). |
| `DRAG`    | Resistencia del agua → velocidad punta. |
| `K_STEER` | Sensibilidad del volante. |

## Circuitos

En el panel ⚙︎ puedes pegar las boyas en orden (la 1ª es salida/meta), en
**metros** `{x,y}` o en **GPS** `{lat,lon}` (se convierten a metros tomando la
1ª boya como origen). Hay modos **Short lap** y **Long lap**.

## Roadmap

- [x] Núcleo jugable: boyas + inclinómetro + modelo de escurrido + sliders
- [x] Fantasma de tu mejor vuelta + Δ en vivo
- [ ] **Solver de línea ideal**: invertir el modelo (`a_lat ≤ A_MAX`) para
      calcular la trazada teóricamente más rápida y el tiempo óptimo, y dibujarla
      como referencia (de juego a entrenador).
- [ ] Boyas con lado (rodear por dentro/fuera), no solo "pasar cerca".
- [ ] Haptics al escurrir; subviraje opcional (te vas largo en vez de frenar).
- [ ] Persistencia de circuitos y leaderboard (reusando el backend Flask).
