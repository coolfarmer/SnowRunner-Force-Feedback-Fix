# Compilation et tests

Tous les chemins de ce guide sont relatifs à la racine du dépôt du plugin
(`release/` lorsqu'il se trouve dans l'espace d'investigation).

## Dépôt autonome

Depuis cette racine, sous Windows x64 avec Python 3.10 ou plus récent et le SDK .NET 10 :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe src/native/fetch_dependencies.py
.\.venv\Scripts\python.exe src/native/build.py
.\.venv\Scripts\python.exe tests/test_native.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File src/installer/build.ps1
.\.venv\Scripts\python.exe src/native/package.py
.\.venv\Scripts\python.exe tests/test_native_install.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tests/test_native_discovery.ps1
.\.venv\Scripts\python.exe tests/test_native_menu.py
.\.venv\Scripts\python.exe tests/test_native_languages.py
.\.venv\Scripts\python.exe tests/test_installer_frontend.py
```

Le téléchargement des dépendances nécessite Internet. LLVM-MinGW portable
20261104 est placé dans `.toolchain/`, sans installation système.
Les téléchargements du compilateur, de MinHook 1.3.4 et du chargeur ASI 10.0.2
sont vérifiés par empreinte ; `vendor/manifest.json` conserve les références.
Pour utiliser une copie existante du même compilateur : définir
`$env:LLVM_MINGW_ROOT` vers son dossier contenant `bin/`, puis lancer la compilation.

`build.py` vérifie les dépendances, compile le plugin et les hôtes de test.
`src/native/game-profile.json` contient uniquement les données de compatibilité
nécessaires au plugin : version et empreinte du jeu, adresse du constructeur,
treize signatures de code. Elles sont compilées dans le plugin ; aucun profil
d'investigation ni logiciel de capture n'est nécessaire.

Exécuter `test_native.py` avant `test_native_menu.py` : ce dernier vérifie que le
plugin empaqueté correspond au binaire testé. Les tests écrivent leurs rapports
dans `logs/` et leurs jeux synthétiques dans `build/`. Ils ne lancent pas SnowRunner
et ne créent aucun périphérique de retour de force.

Le paquet est créé sous `dist/SnowRunnerFFBFix-0.2.0.zip`. Il contient seulement
`Install.cmd` et `Sources/`, organisé en `Installer/`, `Payload/`, `Scripts/`,
`Locales/`, `Docs/` et `Licenses/`. Le manifeste `Sources/package.json` contient
les empreintes avec des chemins relatifs à `Sources/` (révision du paquet 4). Les hôtes de test n'y sont jamais inclus.

`src/installer/` contient l'interface C# Spectre.Console 0.57.2. La publication
autonome Windows x64 embarque .NET 10.0.12, utilise le trimming et regroupe
les bibliothèques dans `Sources/Installer/SnowRunnerFFBFix.Setup.exe`. Le runtime natif
s'extrait au démarrage dans le cache temporaire .NET de Windows. Le SDK n'est
nécessaire que pour compiler. Les dépendances NuGet sont verrouillées par
`packages.lock.json`, téléchargées dans `build/nuget` ; leurs licences sont
incluses dans le paquet. Une mise à jour du runtime doit aussi mettre à jour
le chemin des licences dans `package.py`.

`Install.cmd` lance l'interface, qui appelle le PowerShell système avec une
liste d'arguments séparés (sans construction de commande PowerShell).
Les opérations et protections restent dans `manage.ps1`. Les sorties sont
lues simultanément, puis affichées comme texte, sans interprétation de balisage.
Le menu numérique est utilisé automatiquement en entrée/sortie redirigée,
ou explicitement avec `--plain`. `--preview -Language fr` affiche seulement
un aperçu du menu, sans lancer le gestionnaire ni accéder au jeu.

Le thème interactif utilise un fond `#262626`, du texte `#EEEEEE`, un accent
cyan `#00C8FF` et des informations secondaires `#A0A0A0`. Les séquences OSC
10/11 règlent les couleurs par défaut de la session du terminal ; OSC 110/111
rétablissent celles du profil à la sortie normale ou par Ctrl+C. Aucun fichier
de configuration du terminal n'est modifié. Un terminal ignorant ces séquences
conserve son propre fond. Le mode texte redirigé et `--plain` n'appliquent pas
le thème ; la détection de couleurs de Spectre respecte également `NO_COLOR`.

La compilation et ces tests ne constituent pas une validation en jeu ou matérielle.
Les sorties de compilation, journaux et archives sont ignorés par Git ; le ZIP
peut être joint séparément à une version GitHub.

## Espace de travail d'investigation existant

Dans l'espace local WheelVibratingBug, le Python avec les dépendances de test et
le compilateur sont déjà présents dans le parent. Les dépendances `vendor/`
sont présentes dans ce dépôt. Il n'est pas nécessaire de les télécharger à nouveau.
Depuis **WheelVibratingBug**, exécuter dans PowerShell :

```powershell
$env:LLVM_MINGW_ROOT = (Resolve-Path -LiteralPath '.\.toolchain\llvm-mingw-20261104-ucrt-x86_64').Path
Push-Location -LiteralPath '.\release'
try {
    ..\.venv\Scripts\python.exe src/native/build.py
    ..\.venv\Scripts\python.exe tests/test_native.py
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File src/installer/build.ps1
    ..\.venv\Scripts\python.exe src/native/package.py
    ..\.venv\Scripts\python.exe tests/test_native_install.py
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File tests/test_native_discovery.ps1
    ..\.venv\Scripts\python.exe tests/test_native_menu.py
    ..\.venv\Scripts\python.exe tests/test_native_languages.py
    ..\.venv\Scripts\python.exe tests/test_installer_frontend.py
} finally {
    Pop-Location
}
```

Vérifier la réussite de chaque commande avant de poursuivre. La variable du
compilateur s'applique uniquement à cette session PowerShell. Les sources,
profils, dépendances, paquets et nouveaux rapports restent dans ce dépôt ; seuls
Python et le compilateur sont réutilisés depuis le parent. Les anciens rapports
et l'archive 0.1.0 du parent sont conservés comme historique et retour arrière.
