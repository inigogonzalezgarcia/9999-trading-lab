# Checklist de decisión — leer un backtest

Si falla una de las cinco primeras, deja de leer. Si fallan dos de las restantes, el veredicto es «todavía no sabemos».

- [ ] 1. ¿Están publicados el hash del dataset, la versión de la estrategia y la configuración de ejecución?
- [ ] 2. ¿El motor decide solo con velas cerradas y ejecuta al siguiente precio?
- [ ] 3. ¿Hay spread, deslizamiento y comisión en cada operación, y se dice de dónde salen?
- [ ] 4. ¿Las reglas estaban escritas antes de ver el resultado (fichero con hash, versión nombrada)?
- [ ] 5. ¿Se puede reproducir el número con el código y los datos indicados?
- [ ] 6. ¿Cuántas operaciones hay? ¿Qué pasa con el total si quitas la mejor?
- [ ] 7. Monte Carlo: ¿P25 está por encima de cero? ¿Cuál es la probabilidad de acabar en pérdidas?
- [ ] 8. Benchmark aleatorio: ¿la estrategia supera al 95 % de las entradas al azar con los mismos costes?
- [ ] 9. Sensibilidad: ¿algún parámetro cambia el signo del total al moverlo un paso?
- [ ] 10. Fuera de muestra: ¿hay un tramo reservado con operaciones suficientes para decir algo?
- [ ] 11. Costes: ¿el resultado sobrevive a 0,5 pips más de deslizamiento?
- [ ] 12. ¿El informe termina con una decisión de investigación (descartar, seguir, nueva versión) y no con una invitación a operar?

**Veredicto:** descartar / seguir investigando / nueva versión

_Material educativo. No es asesoramiento de inversión._
