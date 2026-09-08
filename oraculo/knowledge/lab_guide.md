# Anexo A. Laboratorio: Montando la taberna de Moe, auditandola con CAI

## A.1 Introduccion y contexto

El laboratorio se desarrolla sobre una fabrica virtual (Flaming Moe's) que emula una planta embotelladora de bebidas la cual consta de varios componentes:

- 2 depositos de mezcla
- 1 deposito colector
- 1 cinta transportadora de 7 posiciones

En adicion, cada deposito cuenta con control de temperatura y valvulas que permiten mover la mezcla de un deposito a otro.

Todo el proceso esta completamente simulado mediante contenedores Docker, lo que permite reproducir con fidelidad el comportamiento de una instalacion industrial real sin riesgo para personas ni equipos. El entorno incorpora los elementos caracteristicos de un sistema de tecnologias operacionales (OT): un controlador logico programable (PLC) que expone el mapa de bobinas y registros del proceso; los dispositivos de campo simulados (grifos, valvulas, depositos y cinta transportadora), que actuan como sensores y actuadores; un panel de interfaz humano-maquina (HMI) para la supervision y el control; y comunicaciones industriales basadas en los protocolos Modbus TCP y MQTT.

Sobre esta planta se plantean tres ejercicios de dificultad creciente (programacion del PLC, configuracion del HMI y ejecucion de un agente de ciberseguridad basado en IA usando el framework CAI) que se describen en los epigrafes A.6 a A.8.

## A.2 Objetivos de aprendizaje

El objetivo general del laboratorio es que el estudiante adquiera una comprension practica de la seguridad en sistemas OT a partir de la interaccion directa con una planta industrial simulada. Al termino del laboratorio, el estudiante debe ser capaz de:

- describir la arquitectura y los componentes de un sistema OT, asi como sus diferencias frente a un entorno de tecnologias de la informacion (TI)
- programar un PLC en lenguaje de texto estructurado (ST), conforme al estandar IEC 61131-3, utilizando la plataforma abierta OpenPLC
- explicar el funcionamiento del protocolo Modbus TCP: modelo maestro-esclavo, bobinas y registros de retencion (holding registers), y su correspondencia con las direcciones del automata
- comprender el papel del protocolo MQTT en la propagacion de estado entre los dispositivos de campo
- definir que es un HMI dentro de un sistema OT y configurar un panel de supervision y control con la herramienta FUXA
- conocer CAI, un marco de agentes de ciberseguridad basados en modelos de lenguaje de gran tamano (LLM), y configurar un agente orientado al reconocimiento y la explotacion de un entorno controlado
- aplicar tecnicas de diseno de prompts para dirigir de forma efectiva y segura la ejecucion de un agente ofensivo

## A.3 Arquitectura del entorno

La fabrica se despliega integramente mediante Docker Compose y esta formada por los servicios que resume la Tabla A.1.

### Tabla A.1 - Servicios que componen el entorno de laboratorio

| Componente | Servicio | Acceso | Funcion |
|---|---|---|---|
| OpenPLC | openplc | web :8080; Modbus TCP :502 | PLC del proceso: servidor Modbus TCP que aloja el mapa de bobinas y registros |
| FUXA | hmi | web :1881 | HMI: panel de supervision y control del proceso |
| Mosquitto | mosquitto | MQTT :1883 | broker MQTT para la propagacion de estado entre simuladores |
| Dispositivos de campo | tequila, mixtank1, conveyorbelt, drain, etc. | --- | grifos, valvulas, depositos, cinta transportadora y desague, simulados en Python |
| Controlador de proceso | flamingmoes-process | --- | maquina de estados que ejecuta el ciclo de produccion automatico |
| Registro de eventos | opensearch, opensearch-dashboards | API :9200; web :5601 | almacenamiento y consulta de registros de simulacion |
| Agente ofensivo | cai | --- | agente de ciberseguridad basado en LLM, con rol de atacante |
| Asistente | oraculo | --- | asistente conversacional de consulta, en modo solo lectura |

Los contenedores se organizan en tres redes: `ot`, que agrupa el PLC, el HMI, el broker y la pila de observabilidad; `simulators`, donde residen los dispositivos de campo; y `oraculo`, aislada del resto. El agente CAI se conecta a las dos primeras, por lo que alcanza todos los activos del proceso industrial; el Oraculo, en cambio, reside en su propia red y no es alcanzable desde las redes donde opera el agente ofensivo.

El comportamiento global de la planta lo gobierna la bobina 1599 (modo manual): con valor 0, el controlador automatico ejecuta el ciclo de produccion de siete estados (espera y preparacion de depositos, llenado, calentamiento, llenado del colector, refrigeracion y embotellado); con valor 1, el controlador queda a la espera y cada valvula y consigna de temperatura se gobierna manualmente desde el HMI. Tras un reinicio de OpenPLC las bobinas se ponen a 0, por lo que la fabrica arranca siempre en modo automatico.

El mapa completo de direcciones Modbus del proceso se recoge en la Tabla A.2. Cada valvula ocupa dos bobinas consecutivas: la primera recibe la orden (apertura o cierre) y la segunda refleja el estado real comunicado por el simulador. Cada bloque de registros de retencion recoge, en este orden: capacidad actual, capacidades minima y maxima, presiones maxima y minima, presion actual, temperaturas maxima y minima, temperatura actual y nivel de calentamiento o refrigeracion.

### Tabla A.2 - Mapa de direcciones Modbus del proceso

| Direccion | Contenido |
|---|---|
| Bobinas 800-817 | orden y estado de las nueve valvulas (un par por valvula; p. ej., tequila 800/801, brandy 806/807, colector 816/817) |
| Bobina 818 | arranque y paro de la cinta transportadora |
| Bobina 1599 | seleccion del modo manual (1) o automatico (0) |
| Registros 100-109 | parametros del deposito de mezcla 1 (capacidad, min/max, presiones, presion, temp min/max, temp, heat_cool) |
| Registros 110-119 | parametros del deposito de mezcla 2 |
| Registros 120-129 | parametros del colector |

La correspondencia entre direcciones IEC y direcciones Modbus sigue la formula `coil = 8 * palabra + bit`: la direccion %QX199.7 equivale a la bobina `8 * 199 + 7 = 1599`. Las variables se declaran en el bloque VAR con su direccion asociada mediante AT (por ejemplo, `put_valve_status AT %QX100.0 : BOOL`), y el programa se ejecuta ciclicamente cada `T#200ms`.

## A.4 Puesta en marcha

Ni CAI ni el Oraculo arrancan junto con la fabrica: deben iniciarse explicitamente cuando vayan a utilizarse.

### Tabla A.3 - Acceso a los paneles web del laboratorio

| Interfaz | URL | Credenciales |
|---|---|---|
| FUXA (HMI) | http://localhost:1881 | --- |
| OpenPLC | http://localhost:8080 | openplc / openplc |
| OpenSearch Dashboards | http://localhost:5601 | --- |

## A.5 El Oraculo: asistente del laboratorio

Durante todas las sesiones, el estudiante cuenta con un oraculo: un asistente conversacional basado en LLM desplegado dentro del propio entorno. Mientras CAI adopta el papel del atacante, el Oraculo actua como experto del lado de la operacion. Esta disenado para consultas estrictamente en modo lectura: no puede modificar bobinas, registros ni configuraciones, y su red aislada lo mantiene fuera del alcance del agente ofensivo.

El Oraculo puede responder preguntas sobre:

- el funcionamiento de la fabrica: proceso, elementos, modos de control y ciclo de produccion
- las herramientas OT del laboratorio: OpenPLC, FUXA, Modbus TCP, MQTT (Mosquitto), OpenSearch y los simuladores
- la verificacion de la configuracion: contrastar el programa del PLC, los ficheros de configuracion de los simuladores y el proyecto de FUXA contra el mapa documentado

Su uso, interactivo o de una sola pregunta, se realiza desde el contenedor:

```
docker compose exec -it oraculo oraculo              # chat interactivo
docker compose exec -T oraculo oraculo "Esta la fabrica en modo manual?"
```

Cada llamada a una herramienta interna se muestra en pantalla (por ejemplo, `read_modbus(address=1599)`), de modo que el estudiante puede observar como se ha obtenido cada dato. El asistente responde en el idioma en que se formule la pregunta, y constituye la primera fuente de consulta recomendada durante los tres ejercicios.

## A.6 Ejercicio 1: programacion del PLC

**Objetivo.** Familiarizarse con el ciclo de programacion del automata y con el lenguaje ST implementando logica de control propia sobre el mapa de bobinas y registros del proceso.

**Punto de partida.** El programa cargado en OpenPLC (`script.st`) no implementa logica de control: se limita a exponer el mapa de direcciones del proceso, de modo que todo el comportamiento automatico procede del controlador externo. Esta separacion es deliberada y deja al PLC sin logica propia a proposito, para que sea el estudiante quien la dote de contenido.

**Trabajo propuesto.** Implementar en ST una logica de enclavamiento de seguridad sobre el proceso; por ejemplo:

- impedir la apertura de las valvulas de descarga cuando la temperatura del deposito correspondiente quede fuera de su rango permitido
- detener la cinta transportadora si la presion del colector supera su valor maximo
- proponer y justificar cualquier otra logica adicional (parada de emergencia, aviso de nivel, etc.)

**Pistas.**

- La interfaz web de OpenPLC permite editar, compilar y cargar el programa ST.
- La correspondencia entre direcciones IEC y direcciones Modbus sigue la formula `coil = 8 * palabra + bit`: la direccion %QX199.7 equivale a la bobina `8 * 199 + 7 = 1599`.
- Las variables se declaran en el bloque VAR con su direccion asociada mediante AT (por ejemplo, `put_valve_status AT %QX100.0 : BOOL`), y el programa se ejecuta ciclicamente cada `T#200ms` segun la tarea definida en la configuracion.
- Para evitar interferencias con el controlador automatico durante las pruebas, conviene poner la fabrica en modo manual (bobina 1599 a 1).
- Verificar el efecto de la logica implementada desde el HMI o consultando al Oraculo: "Comprueba que el mapeo de coils coincide con script.st".

## A.7 Ejercicio 2: configuracion del HMI en FUXA

**Objetivo.** Comprender la funcion del HMI dentro de un sistema OT y configurar un panel de supervision y control vinculado al PLC mediante Modbus TCP.

**Punto de partida.** La instancia incluye una vista principal con interruptores para las valvulas y la cinta transportadora, indicadores de nivel de los depositos y selectores de consigna de temperatura, todos ellos enlazados a direcciones del mapa Modbus.

**Trabajo propuesto.**

- Explorar la configuracion del dispositivo Modbus TCP (esclavo 1, `openplc:502`) y las etiquetas existentes.
- Anadir un elemento grafico nuevo (indicador, interruptor o grafica) vinculado a alguna direccion del mapa, por ejemplo la temperatura actual del colector, y verificar su funcionamiento.
- Operar la planta desde el panel en modo manual y observar la propagacion de estados (bloqueos por deposito lleno o vacio, parada de grifos aguas arriba).
- Comparar este comportamiento con el modo automatico, donde los mandos del panel reflejan las ordenes emitidas por el controlador.

**Pistas.**

- FUXA esta disponible en http://localhost:1881; el modo de edicion permite modificar la vista y crear etiquetas nuevas.
- Cada elemento grafico se vincula a una etiqueta, y cada etiqueta a un dispositivo, un tipo de direccion (bobina o registro de retencion) y una direccion numerica.
- Ante dudas sobre el significado de una direccion concreta, consultar al Oraculo.

## A.8 Ejercicio 3: diseno de prompts y ejecucion de CAI

**Objetivo.** Configurar un agente de ciberseguridad basado en LLM y disenar prompts que dirijan fases de reconocimiento y explotacion contra la planta, en un entorno cerrado y controlado.

**Punto de partida.** CAI llega preinstalado con el conjunto habitual de herramientas ofensivas (nmap, Metasploit, dirb, gobuster, entre otras) y conectado a las redes `ot` y `simulators`, por lo que alcanza el PLC, el HMI, el broker MQTT y todos los simuladores. El agente por defecto es `redteam_agent`, aunque el comportamiento puede modificarse mediante la variable `CAI_AGENT_TYPE` del fichero de configuracion.

**Fases propuestas.**

1. Reconocimiento: descubrir los hosts vivos y los puertos abiertos en las subredes 172.18.0.0/24 y 172.19.0.0/24.
2. Identificacion: caracterizar los servicios detectados (Modbus en el puerto 502, HTTP en los paneles del PLC y del HMI, MQTT en el 1883) y localizar los activos criticos del proceso.
3. Explotacion controlada: interactuar con el proceso industrial, por ejemplo escribiendo bobinas Modbus para abrir o cerrar valvulas, activar la cinta o conmutar el modo manual, y observar el efecto resultante desde el HMI.

**Diseno de prompts.** La calidad del resultado depende directamente de como se formule la instruccion. Se recomienda:

- ser especifico respecto al objetivo, el alcance y el formato de salida esperado
- incluir restricciones explicitas (subredes permitidas, herramientas preferidas, prohibicion de salir del laboratorio)
- dividir las tareas complejas en pasos iterativos, refinando el prompt a partir de los resultados intermedios
- mantener las salidas pequenas: ordenes como `nmap -n` combinadas con ficheros de salida `-oG` evitan que el agente se bloquee ante resultados muy voluminosos

**Ejecucion.** El agente puede lanzarse en modo interactivo o de una sola orden:

```
docker compose exec -it cai cai "Enumerate both /24 subnets 172.18.0.0/24 and 172.19.0.0/24"
docker compose exec -T cai cai "Scan both subnets and list every host with open ports and identified services"
```

Los objetivos son alcanzables por nombre de servicio (`openplc`, `hmi`, `mosquitto`, `opensearch`) o por direccion IP. El agente persiste su salida en `cai/workspace/`.

**Registro de la experiencia.** Conviene conservar cada prompt empleado junto con su resultado, para analizar posteriormente que formulaciones resultaron mas efectivas y que limitaciones mostro el agente; este registro forma parte de los entregables.

## A.9 Entregables y cuestiones de evaluacion

El laboratorio se evaluara a partir de tres entregables:

1. Programa ST desarrollado en el ejercicio 1, acompanado de una breve explicacion de la logica implementada.
2. Proyecto de FUXA exportado, junto con una captura del panel modificado en funcionamiento (ejercicio 2).
3. Cuaderno de prompts del ejercicio 3: instrucciones utilizadas, resultados obtenidos y analisis critico de la eficacia del agente.

Nota: Este fichero es el contexto del laboratorio para el Oraculo. No contiene soluciones completas, solo objetivos y pistas.
