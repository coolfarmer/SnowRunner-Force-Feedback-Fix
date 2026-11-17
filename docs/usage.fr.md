# SnowRunnerFFBFix — utilisation

Version 0.2.0, révision du paquet 2. Windows 64 bits, SnowRunner Steam
`1.907887.SNOW_DLC_19`. Le plugin reste inactif si ses contrôles de compatibilité
échouent. Seul le Logitech G923 a fait l'objet d'essais physiques antérieurs ;
ce changement du désinstalleur ne constitue pas un nouvel essai en jeu.

Extraire le ZIP dans un dossier séparé du jeu et garder `Install.cmd` avec
`Sources`. Fermer SnowRunner, ouvrir `Install.cmd`, choisir **Français**, puis
**Installer le correctif**. Lancer ensuite le jeu normalement depuis Steam.
Aucun fichier existant n'est écrasé. Une DLL différente ou une configuration
de chargeur inconnue bloque l'installation.

**Consulter son état** affiche le dernier état enregistré ; les compteurs ne
mesurent pas le ressenti du volant. **Autres options** permet de vérifier
l'installation, choisir le dossier du jeu, désactiver ou réactiver le correctif.
La désactivation prend effet au prochain lancement.

## Désinstallation

Fermer SnowRunner, ouvrir `Install.cmd` et choisir **Désinstaller**.
Une question distincte demande si `dinput8.dll` doit être conservé :

- **1 — Oui, conserver (par défaut)** : Entrée choisit cette réponse.
  Le plugin est retiré et le chargeur reste en place pour les autres mods.
- **2 — Non, demander le retrait de dinput8.dll** : le retrait n'est permis
  que si notre installation l'a ajouté, s'il est inchangé et si aucun autre
  plugin `.asi` n'est détecté dans le dossier du jeu et ses sous-dossiers.
- **0 — Annuler la désinstallation** : aucun fichier n'est modifié.

Une fin d'entrée avant la réponse annule également l'opération. Un fichier
préexistant ou partagé est conservé même si son retrait est demandé. Si un
fichier à retirer a été modifié, la désinstallation s'arrête avant toute
suppression. Une DLL modifiée n'empêche pas de désinstaller le correctif lorsque
**Oui, conserver** est choisi. Le journal de diagnostic reste conservé.

La recherche des `.asi` ne garantit pas l'absence de toute autre dépendance au
chargeur. Conserver `dinput8.dll` reste le choix recommandé en cas de doute.
Après une désinstallation avec conservation, le reçu du correctif est retiré ;
une réinstallation considère alors cette DLL comme préexistante et la protège.
Le choix de retrait est proposé pendant la désinstallation, pas comme un outil
de nettoyage de DLL sans reçu d'installation.

Pour les scripts : `Sources/manage.ps1 -Action Uninstall -GameDirectory <dossier>`
conserve le chargeur sans question interactive. Ajouter `-RemoveLoader` demande
son retrait avec les mêmes protections. Le menu fournit le choix interactif.

Avant une mise à jour, désinstaller l'ancienne version, jeu fermé. Garder
l'ancien paquet pour permettre un retour arrière. Ni l'exécutable du jeu sur
disque ni les DLL système Windows ne sont modifiés.
