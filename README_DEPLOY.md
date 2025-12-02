# Opciones gratuitas para publicar y proteger los reportes

Este documento resume alternativas sin desembolso (o con capa gratuita) para que tu app/reportes estén accesibles 24/7 incluso cuando tu PC esté apagado, junto con recomendaciones de seguridad para datos confidenciales.

---

## Requisitos previos (comunes)
- Tener el código de la app (`app.py`, `requirements.txt`) en un repositorio (GitHub recomendado).
- Separar los datos confidenciales del repositorio (no subir el `.xlsm` con datos sensibles a un repo público).
- Conocer a los usuarios que necesitarán acceso (lista de correos o IPs) para configurar acceso restringido.

---

## Opciones viables (sin coste directo)

1) Oracle Cloud Free Tier (recomendado si quieres control y privacidad)
- Qué es: Oracle ofrece instancias "Always Free" (VMs) que puedes mantener encendidas permanentemente.
- Pros: control total del servidor, puedes instalar Python + Streamlit, configurar HTTPS, autenticación, firewall.
- Contras: requiere alta responsabilidad (actualizar, parchear), registro con tarjeta para verificación.
- Seguridad: alojas los ficheros localmente en la VM, usas `nginx` con HTTP Basic Auth o `Cloudflare Access` + `Let's Encrypt` para TLS.
- Nivel técnico: medio-alto (configurar Linux, systemd, nginx).
- Recomendación: buena opción para datos confidenciales cuando no quieres pagar.

2) Streamlit Community Cloud (rápido y simple)
- Qué es: plataforma de Streamlit para desplegar apps desde GitHub.
- Pros: despliegue muy simple (push -> app), ideal para pruebas y demos.
- Contras: normalmente requiere repositorio público en el plan gratuito (si tu repo es público no usarlo con datos sensibles). Manejo de secretos posible pero el código y assets en repo público son riesgosos.
- Seguridad: NO subir archivos con datos sensibles al repo; usar fuentes de datos seguras (p. ej. bucket S3 con credenciales) y `st.secrets` para credenciales (pero las credenciales deben mantenerse seguras fuera del repo). Para datos corporativos confidenciales no es la opción más segura en su plan gratuito.
- Nivel técnico: bajo.

3) GitHub Actions + GitHub Pages (reportes estáticos)
- Qué es: programar una acción (`workflow`) que crea snapshots (HTML/PDF) periódicamente y publica en GitHub Pages.
- Pros: No necesitas servidor, es barato (gratis), y la web será estática (fast, simple). HTML o PDF pueden ser descargados por gerencia.
- Contras: GitHub Pages suele ser para contenido público (exponería datos si la página es pública). Publicar desde repositorio privado puede requerir plan o configuración adicional.
- Seguridad: si hay necesidad estricta de privacidad, no usar Pages público; en su lugar publicar en un servidor propio.
- Nivel técnico: medio (escribir workflow y convertir DataFrame -> HTML/PDF sin exponer datos).

4) VPS gratuito o 'zero-cost' personal + Cloudflare Tunnel
- Qué es: mantener un dispositivo/VM pequeño (p. ej. Raspberry Pi o VM en Oracle Free Tier) y exponerlo de forma segura con Cloudflare Tunnel (gratuito en plan básico) y reglas de acceso.
- Pros: control, puedes restringir acceso por cuenta (Cloudflare Access) o por IP.
- Contras: implica gestionar infraestructura y la seguridad de la máquina.
- Nivel técnico: medio-alto.

---

## Recomendación práctica (mi sugerencia)
Si quieres privacidad y no pagar, la opción más práctica y segura es:
- Crear una VM "Always Free" (Oracle Cloud Free Tier) o usar un VPS gratuito similar.
- Instalar Python y ejecutar la app detrás de `nginx` con HTTPS (Let's Encrypt).
- Proteger la app con HTTP Basic Auth (o mejor, con Cloudflare Access si quieres SSO) y no exponer el `.xlsm` en repositorio.

Si prefieres simplicidad y aceptas mantener los datos fuera del repositorio (por ejemplo en un bucket privado o base de datos), Streamlit Community Cloud es la ruta más rápida.

---

## Plantillas / comandos (Ubuntu 22.04 LTS) para desplegar en una VM (paso a paso resumido)

1) Crear VM y conectar por `ssh`.
2) Actualizar e instalar dependencias:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx git apache2-utils
```

3) Preparar la app (ejecutar como usuario no root):

```bash
cd /home/ubuntu
git clone <TU_REPO_PRIVADO_O_PUBLICO>
cd <tu-repo>
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
# mover tus datos sensibles al servidor (por SCP) y asegurarte permisos 600
chmod 600 data/BBDD_MANTENCION.xlsm
```

4) Crear servicio systemd para Streamlit (archivo: `/etc/systemd/system/streamlit-app.service`):

```
[Unit]
Description=Streamlit App
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/<tu-repo>
Environment="PATH=/home/ubuntu/<tu-repo>/.venv/bin"
ExecStart=/home/ubuntu/<tu-repo>/.venv/bin/python -m streamlit run app.py --server.headless true --server.port 8501 --server.address 127.0.0.1
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Activar y arrancar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable streamlit-app
sudo systemctl start streamlit-app
sudo systemctl status streamlit-app
```

5) Configurar `nginx` como reverse proxy y protección básica (archivo: `/etc/nginx/sites-available/streamlit`):

```
server {
    listen 80;
    server_name tu.dominio.o.ip;

    location / {
        proxy_pass http://127.0.0.1:8501/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }
}
```

Habilitar sitio y obtener certificado TLS (Let's Encrypt):

```bash
sudo ln -s /etc/nginx/sites-available/streamlit /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo certbot --nginx -d tu.dominio.o.ip
```

6) Añadir autenticación básica (opcional, simple y efectiva):

```bash
# crear archivo con usuario y contraseña (instala apache2-utils previamente)
sudo htpasswd -c /etc/nginx/.htpasswd gerencia
# luego editar el bloque location / en el config de nginx y añadir:
# auth_basic "Restricted";
# auth_basic_user_file /etc/nginx/.htpasswd;
sudo nginx -t
sudo systemctl reload nginx
```

Con esto tendrás la app disponible con HTTPS y autenticación básica.

---

## Seguridad y privacidad (puntos clave)
- No subas `BBDD_MANTENCION.xlsm` a un repo público.
- Usa SSH keys para `git clone` de repos privados, o SFTP para subir los datos directamente a la VM.
- Aplica TLS (Let's Encrypt) y usa autenticación (al menos Basic Auth) para evitar exposición pública.
- Mantén el sistema actualizado y crea backups cifrados de los datos.
- Considera agregar un WAF/Cloudflare delante del servidor para protección adicional y limitación por IP.

---

## Si quieres hoy: opciones rápidas
- Si quieres que yo genere los archivos de ejemplo (systemd unit, `nginx` config, script de deploy) los creo en el repositorio para que puedas copiarlos y adaptarlos.
- Dime qué prefieres: "Oracle VM (guía completa)" o "Streamlit Community Cloud (rápido)" o "Snapshots estáticos con GitHub Actions".

---

Ficha rápida de decisiones:
- Privacidad fuerte + sin coste → VM Always Free (Oracle) + nginx + certbot + basic auth.
- Muy rápido, poco control → Streamlit Community Cloud (evitar datos sensibles en repo).
- Sólo lectura y sin servidor → GitHub Actions -> GitHub Pages (si publicar públicamente es aceptable).

