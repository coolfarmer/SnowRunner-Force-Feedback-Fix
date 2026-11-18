# SnowRunnerFFBFix — utilisation

Version 0.2.0, révision du paquet 5. Windows 64 bits, SnowRunner Steam
`1.907887.SNOW_DLC_19`. Le plugin reste inactif si ses contrôles de compatibilité
échouent. Seul le Logitech G923 a fait l'objet d'essais physiques antérieurs ;
cette modification de l'installateur ne constitue pas un nouvel essai en jeu.

Extraire le ZIP dans un dossier séparé du jeu et garder `Install.cmd` avec
`Sources`. Fermer SnowRunner, ouvrir `Install.cmd`, choisir **Français**, puis
**Installer le correctif**. Lancer ensuite le jeu normalement depuis Steam.
Aucun fichier existant n'est écrasé. Le chargeur de mods est géré automatiquement :
s'il est absent, l'installateur ajoute celui du paquet ; s'il est reconnu, il est
réutilisé. Les copies x64 vérifiées d'Ultimate ASI Loader 10.0.2 et 8.5.0 (celle de
SMT v1.5) sont reconnues par leur empreinte exacte. Une DLL ou une configuration
de chargeur inconnue bloque l'installation sans modifier les fichiers existants.
Les tests de chargement hors jeu avec 8.5.0 réussissent ; le fonctionnement du
correctif avec le vrai mod SMT dans SnowRunner reste à valider.

Le menu Spectre.Console se parcourt avec les flèches et Entrée. L'interface
embarque .NET : aucun runtime supplémentaire n'est à installer. Windows
PowerShell 5.1 exécute les opérations d'installation. Le paquet extrait doit
rester complet ; l'interface n'est pas copiée dans le jeu.
`Install.cmd --plain` propose un menu numéroté ; ce mode est automatique si
l'entrée ou la sortie est redirigée. Le menu PowerShell d'origine reste accessible
avec `powershell.exe -NoProfile -ExecutionPolicy Bypass -File Sources/Scripts/menu.ps1`.

**Consulter son état** affiche le dernier état enregistré ; les compteurs ne
mesurent pas le ressenti du volant. **Autres options** permet de vérifier
l'installation, choisir le dossier du jeu, désactiver ou réactiver le correctif.
La désactivation prend effet au prochain lancement.

## Désinstallation

Fermer SnowRunner, ouvrir `Install.cmd` et choisir **Désinstaller**.
La désinstallation démarre directement, sans question sur les DLL.

- Un chargeur présent avant notre installation est toujours conservé.
- Un chargeur ajouté par notre installation est retiré s'il est reconnu,
  inchangé et qu'aucun indice d'utilisation par un autre mod n'est détecté.
- Un chargeur modifié, partagé, inaccessible ou dont l'utilisation est incertaine
  est conservé ; cela n'empêche pas le retrait de notre plugin.

La détection examine aussi les plugins masqués, les sous-dossiers, les fichiers
de configuration connus, les DLL chaînées et les sources `.cxx`. Un dossier
redirigé, une erreur de lecture ou un arbre trop volumineux entraîne la
conservation du chargeur. Cette détection ne prouve pas l'absence de toute
dépendance possible d'un autre mod.

Si le plugin lui-même a été modifié, l'opération s'arrête avant toute suppression.
Le journal est conservé. Le reçu mémorise l'empreinte réelle du chargeur réutilisé
et sa provenance ; il est retiré lors de la désinstallation. Un chargeur conservé
sera considéré comme préexistant lors d'une réinstallation.

Pour les scripts : `Sources/Scripts/manage.ps1 -Action Uninstall -GameDirectory <dossier>`
applique les mêmes règles automatiquement. L'ancien paramètre `-RemoveLoader`
reste accepté pour les scripts existants, sans changer ces règles.

Avant une mise à jour, désinstaller l'ancienne version, jeu fermé. Garder
l'ancien paquet pour permettre un retour arrière. Ni l'exécutable du jeu sur
disque ni les DLL système Windows ne sont modifiés.
