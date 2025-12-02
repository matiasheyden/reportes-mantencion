# Despliegue paso a paso (resumen práctico)

Este archivo explica, de forma concreta, cómo dejar la app accesible 24/7 en una VM Ubuntu (Oracle Cloud Free Tier) y cómo mantener el Excel actualizado.

1) Crear cuenta en Oracle Cloud Free Tier
- Regístrate en https://www.oracle.com/cloud/free/ y crea una "Always Free" VM (Ubuntu 22.04). Guarda la IP pública y configura una clave SSH.

2) Conectarte por SSH a la VM

```bash
ssh -i /path/to/your_key.pem ubuntu@YOUR_VM_IP
```

3) Ejecutar el script de despliegue en la VM
- Copia `deploy_to_vm.sh` al servidor (por `scp`) o pega su contenido y ejecútalo:

```bash
# en tu máquina local (desde el proyecto)
scp deploy_to_vm.sh ubuntu@YOUR_VM_IP:~/
ssh -i /path/to/key ubuntu@YOUR_VM_IP 'bash ~/deploy_to_vm.sh'
```

Nota: edit `deploy_to_vm.sh` y reemplaza `YOUR_DOMAIN_OR_IP` en la sección de nginx y ajusta `REPO_URL` si vas a clonar desde git.

4) Subir el archivo Excel y ajustar permisos

```bash
scp BBDD_MANTENCION.xlsm ubuntu@YOUR_VM_IP:/home/ubuntu/streamlit_reportes/BBDD_MANTENCION.xlsm
ssh ubuntu@YOUR_VM_IP 'chmod 600 /home/ubuntu/streamlit_reportes/BBDD_MANTENCION.xlsm; sudo systemctl restart streamlit-reportes.service'
```

5) Configurar DNS y HTTPS (opcional pero recomendado)
- En tu proveedor de DNS crea un A record apuntando `reportes.tuempresa.com` a la IP de la VM.
- En la VM ejecuta (reemplazando el dominio):

```bash
sudo certbot --nginx -d reportes.tuempresa.com
```

6) Actualizar Excel desde tu PC (flujo recomendado)
- Opción A (manual): usa `sync_excel.sh` desde tu máquina local:
  ```bash
  ./sync_excel.sh ubuntu@YOUR_VM_IP /home/ubuntu/streamlit_reportes/BBDD_MANTENCION.xlsm
  ssh ubuntu@YOUR_VM_IP 'sudo systemctl restart streamlit-reportes.service'
  ```
- Opción B (SFTP): abrir un cliente SFTP (WinSCP, FileZilla) y arrastrar el archivo al path indicado.

7) Acceso por gerencia
- Si configuraste HTTPS y (opcional) auth: comparte la URL `https://reportes.tuempresa.com` con gerencia y distribuye el atajo `management_shortcut.url` (reemplazado con la URL real).

---

Si quieres, puedo:
- Generar automáticamente los comandos con tu IP o dominio (dímelos) y reemplazar placeholders en los archivos del proyecto.
- Preparar un script de subida automática (cron) o un workflow que suba el Excel a la VM desde una carpeta local.
