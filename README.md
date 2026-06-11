# 🏃‍♂️ infame-Elite-Endurance-Coach-GEM

Bienvenido al repositorio central de **infame-Elite-Endurance-Coach**. Este espacio está diseñado para almacenar, estructurar y mantener actualizadas las metodologías, planes de entrenamiento y directrices del entrenador virtual.

El objetivo de este sistema es prescribir cargas de trabajo óptimas y personalizadas para atletas de resistencia, optimizando el rendimiento tanto en asfalto como en montaña.

---

## 🗺️ Estructura del Repositorio

Para mantener el orden y facilitar la actualización del GEM, los archivos `.md` se organizan de la siguiente manera:

*   📂 `metodologias/`: Bases teóricas, umbrales y principios de entrenamiento.
*   📂 `planes/`: Estructuras de entrenamiento por disciplina (Trail Running, Ruta, etc.).
*   📂 `atletas/`: (Opcional/Privado) Plantillas de seguimiento o perfiles.

---

## 📑 Principios de Prescripción Básicos

Para garantizar la coherencia en las respuestas del GEM, toda la prescripción de entrenamientos debe seguir estas reglas por defecto:

### 🌲 Trail Running
*   **Métrica Principal:** Por defecto, los entrenamientos se deben prescribir siempre en **%LTHR** (Lactate Threshold Heart Rate).
*   **Métrica Secundaria:** Seguidos estrictamente por **RPE** (Rate of Perceived Exertion / Escala de Esfuerzo Percibido) para gestionar la variabilidad del terreno.
*   *Excepción:* Esta regla solo se rompe si el corredor cuenta específicamente con un **potenciómetro para correr** (vatios), en cuyo caso se priorizará la potencia.

### 🚴‍♂️ Ciclismo / Multisport (Ruta y Virtual)
*   Uso de potencia y zonas de frecuencia cardíaca estructuradas según la disponibilidad de hardware del atleta.

---

## 🔄 Control de Cambios (Versionado)

*   **v3.0 (Actual):** Migración del sistema a repositorio Git. Organización de archivos Markdown por categorías para facilitar la actualización continua del GEM.
*   **Próximos pasos:** Integración de prompts estructurados y automatización de plantillas de feedback semanal.

---

## 🛠️ Cómo Actualizar el GEM

Cada vez que agregues un nuevo plan o modifiques una metodología en tus archivos locales, ejecuta el flujo estándar en tu terminal:

```bash
git add .
git commit -m "Actualización: [Breve descripción del cambio]"
git push origin main
