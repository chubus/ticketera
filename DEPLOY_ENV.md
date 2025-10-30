Recomendación de variables de entorno para Deploy (Ticketera/DevOps)

Obligatorias (producción):
- FLASK_ENV=production
- BELGRANO_AHORRO_URL=https://belgranoahorro-hp30.onrender.com
- BELGRANO_AHORRO_API_KEY=REEMPLAZAR_CON_API_KEY_REAL
- DATABASE_URL=postgresql+psycopg2://user:password@host:5432/tickets
- SECRET_KEY=REEMPLAZAR_CON_SECRETO_SEGURO

Opcionales:
- API_TIMEOUT_SECS=30
- API_RETRY_TOTAL=3
- API_RETRY_BACKOFF=0.5
- DEVOPS_API_URL=https://tu-ticketera.tu-dominio.com
- DEVOPS_API_KEY=REEMPLAZAR_SI_APLICA

Notas:
- En producción no se usan valores por defecto para URL/API Key.
- Si no se establece DATABASE_URL, la app avisará que sqlite no es válido en producción.

