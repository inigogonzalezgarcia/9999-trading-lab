# Informe de backtest — <hipótesis> <versión>

> Material educativo. Resultados simulados sobre datos históricos. No es asesoramiento de inversión. El rendimiento pasado no garantiza resultados futuros.

| Campo | Valor |
|---|---|
| Fecha del informe | AAAA-MM-DD |
| Autor | |
| Versión de la estrategia | V_._ (`fichero.yaml`, hash `…`) |
| Cambios respecto a la versión anterior | … (enlace al log de decisiones) |
| Software | versión · revisión |

## 1. Hipótesis
Qué afirma la regla, en una frase. Qué mercado, qué horario, qué dirección. Qué debería verse si es cierta y qué debería verse si es falsa.

## 2. Datos
| Campo | Valor |
|---|---|
| Proveedor y tipo | (p. ej. ticks agregados a M1) |
| Símbolo(s) | |
| Rango (UTC) | |
| Zona horaria de las reglas | (p. ej. Europe/Madrid, tzdata …) |
| SHA-256 del dataset | |
| Filas · huecos · duplicadas · inválidas | |
| Columna de spread disponible | sí / no |

## 3. Ejecución y costes
| Campo | Valor |
|---|---|
| Modelo de relleno | (decisión al cierre, ejecución al siguiente precio) |
| Spread | origen y valor |
| Deslizamiento | pips, ¿también en el stop? |
| Comisión | |
| Riesgo por operación | fracción del capital |
| Expiración por sesión | sí / no, hora |

## 4. Resultado
| Métrica | Valor |
|---|---|
| Operaciones (N) | |
| Esperanza (R) | |
| Acierto | |
| Ganancia media / pérdida media (R) | |
| Factor de beneficio | |
| Drawdown máximo (R) | |
| Total R | |
| **Total R sin la mejor operación** | |

Motivos de salida: stop … · objetivo … · fin de sesión …

Curva de capital (en R, eje X = operaciones): *insertar figura*.

## 5. Protocolo
### 5.1 Monte Carlo
| Percentil | R final | Drawdown máx. |
|---|---|---|
| P5 | | |
| P25 | | |
| P50 | | |
| P75 | | |
| P95 | | |

Probabilidad de acabar en pérdidas: … %. Simulaciones: … · semilla: …

### 5.2 Benchmark aleatorio
Esperanza de la regla … R · esperanza aleatoria P50 … R · P95 … R · percentil de la regla … % · p-valor empírico …

### 5.3 Sensibilidad
| Parámetro | Valor | N | Total R | Esperanza |
|---|---|---|---|---|
| | | | | |

Parámetros que cambian el signo: …

### 5.4 Particiones y walk-forward
| Tramo | Días | N | Total R | Esperanza |
|---|---|---|---|---|
| entrenamiento | | | | |
| validación | | | | |
| fuera de muestra | | | | |

Walk-forward: ventanas … · con operaciones … · positivas … · total fuera de muestra … R

## 6. Limitaciones
- Relleno simulado sobre datos históricos; sin ejecución real.
- …

## 7. Decisión
Una de: **descartar** / **seguir investigando** (con qué dato nuevo) / **nueva versión** (con qué cambio exacto, y por qué).

Entrada en el log de decisiones: `AAAA-MM-DD — …`

## 8. Checklist
Pegar aquí la checklist del kit (03-checklist) con cada pregunta respondida.
