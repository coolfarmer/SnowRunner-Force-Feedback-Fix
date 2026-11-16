# SnowRunner Force Feedback Fix

Correctif natif expérimental **0.2.0** pour les oscillations anormales du volant
lors de certains changements de carte dans SnowRunner, sur Windows x64 / Steam.

Il initialise quatre champs (16 octets) à l'entrée d'un constructeur du jeu.
Il conserve le fonctionnement du retour de force : aucun plafond de force,
changement de gain ou réinitialisation périodique n'est ajouté.

## Installation et utilisation

Le paquet généré est `dist/SnowRunnerFFBFix-0.2.0.zip`.
Extraire entièrement le ZIP dans un dossier séparé du jeu, ouvrir `Install.cmd`,
choisir Français ou English, puis installer. Lancer ensuite le jeu depuis Steam.
Le même menu permet de consulter l'état, désactiver, réactiver et désinstaller.
Fermer le jeu avant toute modification de l'installation.

- [Guide français](docs/usage.fr.md)
- [English guide](docs/usage.en.md)
- [Compilation et tests](docs/build.md)

Le téléchargement GitHub « Code → Download ZIP » contient les sources ;
il faut les compiler pour obtenir le paquet installable. Python et le compilateur
ne sont pas nécessaires pour utiliser un paquet déjà compilé.

## Compatibilité et validation

Seul l'exécutable Steam **1.907887.SNOW_DLC_19** est accepté, avec son empreinte
SHA-256 et treize plages de code contrôlées. Une version inconnue laisse le
correctif inactif. Les contrôles sont compilés dans le plugin.

La version 0.1.0 a donné des résultats favorables sur un Logitech G923 : onze
transitions explicitement comptées et d'autres transitions non quantifiées,
sans oscillation et avec retour de force normal selon l'utilisateur.
**La version 0.2.0 n'a pas encore été essayée en jeu ni validée physiquement.**
Elle retire l'exigence du SDK Logitech, sans changer l'initialisation des champs.
Les autres modèles de volant et l'impact quantitatif sur les performances
restent à valider. Les tests automatisés utilisent des hôtes synthétiques.

## Contenu du dépôt

- `src/native/` : plugin, installateur bilingue, profil de compatibilité et outils de compilation.
- `tests/` : tests du correctif et de l'installateur, sans utilisation du volant.
- `vendor/` : dépendances nécessaires et leurs licences / empreintes.
- `docs/` : utilisation et compilation.

Les captures et outils d'investigation ne font pas partie de ce dépôt.
Les sorties `build/`, `dist/` et `logs/` sont locales et ignorées par Git.

## Dépendances et licences

Ultimate ASI Loader 10.0.2 charge le plugin via un `dinput8.dll` local au jeu.
MinHook 1.3.4 est lié statiquement. Leurs notices figurent dans
[vendor/ultimate-asi-loader/LICENSE.txt](vendor/ultimate-asi-loader/LICENSE.txt)
et [vendor/minhook/LICENSE.txt](vendor/minhook/LICENSE.txt), et sont incluses
dans le paquet. Aucune licence propre au code du correctif n'a encore été choisie ;
les licences des dépendances ne s'étendent pas automatiquement à celui-ci.
