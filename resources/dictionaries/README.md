# Diccionarios y listas editables para el pipeline de anonimización.
#
# Cualquier archivo aquí puede ser modificado SIN TOCAR CÓDIGO PYTHON.
# El servidor los carga automáticamente al arrancar.
#
# Archivos:
#   whitelist.txt     → Términos clínicos que NO se anonimizan
#   stopwords.txt     → Palabras funcionales ES/CA que no son entidades
#   clinical_words.txt→ Palabras clínicas (falsos positivos en modo derivado)
#   entidades.csv     → Diccionario de entidades conocidas (nombres, centros, etc.)
#                       columnas: tipo, valor, es_original
#                        tipo: PERSON, LOCATION, etc.
#                        es_original: 1=original, 0=derivada
#