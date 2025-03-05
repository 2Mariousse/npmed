import requests
import os
import subprocess
from termcolor import colored
import json
import tarfile
import shutil
import time
from requests.exceptions import ChunkedEncodingError


with open("blacklist.txt", "r", encoding="utf-8") as f:
    blacklist = [line.strip() for line in f if line.strip()]

# URL de l'API des changements continus de npm
URL = "https://replicate.npmjs.com/_changes?feed=continuous&since=now"

# Dossiers où télécharger et extraire les paquets
DOWNLOAD_DIR = "downloads"
EXTRACTED_DIR = "extracted"
output_file="scan_results.txt"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(EXTRACTED_DIR, exist_ok=True)

# Fonction pour télécharger le paquet tarball depuis le registre npm
def download_package(package_name):
    print(colored(f"Téléchargement du paquet : {package_name}", "red"))
    try:
        # Construire l'URL du paquet tarball
        package_url = f"https://registry.npmjs.org/{package_name}/latest"
        
        # Effectuer la requête GET pour obtenir les métadonnées du paquet
        response = requests.get(package_url)
        if response.status_code == 200:
            data = response.json()
            tarball_url = data["dist"]["tarball"]
            
            # Télécharger le tarball dans le dossier 'downloads'
            tarball_path = os.path.join(DOWNLOAD_DIR, f"{package_name}.tgz")
            tarball_response = requests.get(tarball_url)
            
            with open(tarball_path, "wb") as f:
                f.write(tarball_response.content)
            print(colored(f"Paquet {package_name} téléchargé avec succès.", "green"))
            
            # Extraire le tarball dans le dossier 'extracted'
            extract_path = os.path.join(EXTRACTED_DIR, package_name)
            with tarfile.open(tarball_path, "r:gz") as tar:
                tar.extractall(path=extract_path)
            print(colored(f"Paquet {package_name} extrait dans {extract_path}.", "green"))

            if os.path.isdir(extract_path+"/package"):
                os.rename(extract_path+"/package",extract_path+"/dummy")
            else:
                print("AHALALAZUT")

            # Analyser le paquet avec ggshield
            print(colored(f"Analyse du paquet {package_name} avec ggshield...", "blue"))
            result = subprocess.run(["ggshield", "secret", "scan", "--show-secrets", "path", extract_path,"--recursive", "-y"], capture_output=True, text=True)
            
            # Afficher les résultats de l'analyse
            if result.returncode == 0:
                print(colored(f"Analyse réussie pour {package_name}:\n{result.stdout}", "green"))
                
            else:
                print(colored(f"Analyse échouée pour {package_name}", "yellow"))
                with open(output_file, "a") as f:
                    f.write(f"Résultats pour {package_name}:\n")
                    f.write(result.stderr)
                    f.write(result.stdout)
                    f.write("\n" + "="*80 + "\n")
                    print(f"Résultats sauvegardés dans {output_file}")
            
            
            # Supprimer le fichier tarball téléchargé
            os.remove(tarball_path)
            print(colored(f"Fichier {tarball_path} supprimé.", "green"))
            
            # Supprimer le dossier extrait
            shutil.rmtree(extract_path)
            print(colored(f"Dossier {extract_path} supprimé.", "green"))
            
        else:
            print(colored(f"Erreur lors du téléchargement du paquet {package_name}. {response.json()}", "yellow"))
            if "latest" in response.json():
                package_url = f"https://registry.npmjs.org/{package_name}"
                response = requests.get(package_url)
                #no version released : public but no public version
                if response.json().get("versions")!={}:
                    breakpoint()
    except Exception as e:
        print(colored(f"Erreur dans le processus de téléchargement ou d'extraction pour {package_name}: {e}", "yellow"))

# Fonction pour analyser les lignes de changement
def analyze_change(change):
    try:
        # Convertir la ligne en JSON
        change_data = json.loads(change)
        package_name = change_data["id"]
        is_deleted = change_data.get("deleted", False)

        # Vérifier si le package est supprimé ou scopé (ex: @scope/package)
        if is_deleted or package_name.startswith("@") or package_name in blacklist:
            return

        # Récupérer les métadonnées du package
        package_url = f"https://registry.npmjs.org/{package_name}"
        response = requests.get(package_url)

        if response.status_code == 200:
            data = response.json()
            latest_version = data.get("dist-tags", {}).get("latest")

            if not latest_version:
                print(colored(f"⚠️  Aucun 'latest' pour {package_name}, ajout à la blacklist.", "yellow"))
                with open("blacklist.txt", "a") as f:
                    f.write(f"{package_name}\n")
                    blacklist.append(package_name)
                return  # Ignore ce package

            # Si tout va bien, on continue le process
            print(colored(f"📦 Changement détecté pour : {package_name} (version {latest_version})", "yellow"))
            download_package(package_name)

        else:
            print(colored(f"❌ Erreur en récupérant {package_name}. Code: {response.status_code}", "red"))

    except json.JSONDecodeError:
        print(colored("⚠️ Erreur de décodage JSON dans la ligne de changement", "yellow"))


# Fonction pour écouter les changements en temps réel
def listen_changes():
    while True:
        try:
            with requests.get(URL, stream=True,timeout=10) as response:
                # Lire les lignes du flux de changements
                for line in response.iter_lines():
                    if line:
                        # Analyser et afficher chaque ligne de manière appropriée
                        analyze_change(line.decode("utf-8"))
        except ChunkedEncodingError:
            print(colored("Connexion interrompue, nouvelle tentative...","red"))
            time.sleep(2)

# Fonction principale pour démarrer l'écoute
def main():
    print(colored("Démarrage de l'écoute des changements npm...", "blue"))
    listen_changes()

# Exécution principale
if __name__ == "__main__":
    main()
