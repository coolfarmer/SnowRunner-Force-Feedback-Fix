# SnowRunnerFFBFix 0.2.0 — utilisation

Plugin expérimental pour Windows x64 / Steam. Extraire le ZIP complet,
garder `Install.cmd` et le dossier `Sources` ensemble, puis ouvrir `Install.cmd`.
Choisir **Français**. L'ouverture du menu ne modifie pas le jeu.

## Installation

1. Fermer SnowRunner.
2. Choisir **Installer le correctif**. Les vérifications sont automatiques.
3. Après confirmation de réussite, lancer le jeu normalement depuis Steam.
4. **Consulter son état** affiche l'état enregistré du plugin.

Pour remplacer une version installée, la désinstaller d'abord, jeu fermé.
Conserver l'ancien paquet pour revenir à cette version par désinstallation puis
réinstallation. Aucun fichier préexistant n'est écrasé. Un chargeur identique
peut être réutilisé ; une autre DLL ou une configuration existante provoque un refus.
Le menu n'élève pas automatiquement les privilèges.

**Autres options** permet de vérifier la compatibilité, désactiver, réactiver
ou saisir manuellement le dossier du jeu (ou son sous-dossier `Sources\Bin`).
La langue peut être changée dans le menu. Python et Frida ne sont pas nécessaires.

## Compatibilité et fonctionnement

Exécutable accepté : **1.907887.SNOW_DLC_19**, Steam Windows x64.
SHA-256 : `d46623b23808d19a40f7ebeec15332d11f97317637ec4d4e072a501bc78a77c8`.
Treize plages de code chargé sont également vérifiées avant l'activation.
Modifier `Sources/package.json` ne contourne pas les contrôles du plugin.
Après une mise à jour inconnue, le correctif reste inactif ; une nouvelle validation
est nécessaire. Le refus est testé sur des hôtes synthétiques.

Ultimate ASI Loader 10.0.2 (`dinput8.dll`) charge `SnowRunnerFFBFix.asi`.
Le plugin utilise MinHook 1.3.4 pour initialiser seulement `this+0x44..0x53`
avant le constructeur original. Les écritures légitimes du jeu restent possibles.
Il n'ajoute ni filtre de force, ni changement de gain, ni remise à zéro périodique.
L'exécutable du jeu sur disque et les DLL système Windows ne sont pas modifiés.
Le plugin n'exige pas G HUB ou le SDK Logitech ; le jeu conserve ses propres
besoins en pilotes et SDK. Cela n'ajoute pas de nouveaux volants pris en charge.

## État et désinstallation

Le journal `SnowRunnerFFBFix.log`, à côté du plugin, indique :

- `ACTIVE`, `armed=1` : hook installé ; `applied` compte les initialisations.
- `INACTIVE` : refus de compatibilité ou erreur d'installation du hook.
- `DISABLED` : marqueur de désactivation présent au lancement.
- `DISARMED`, `failed>0` : erreur mémoire, initialisations suivantes désactivées.

Un journal peut provenir d'une ancienne session. `applied=0` au menu peut être normal.
Ces compteurs ne mesurent pas la force physique du volant.
Les erreurs système détaillées de l'installateur sont enregistrées dans
`Sources/setup-diagnostic.log` si le dossier est accessible en écriture.

Jeu fermé, **Désactiver temporairement** prend effet au prochain lancement ;
**Réactiver** retire ce marqueur. **Désinstaller** retire seulement les fichiers
ajoutés dont les empreintes sont inchangées. Les fichiers modifiés, chargeurs
préexistants ou partagés avec d'autres plugins et le journal sont préservés.
Le plugin ne se décharge pas à chaud. Sa désactivation n'arrête pas les forces
déjà envoyées au volant.

## Limites des essais

La version 0.1.0 a été essayée sur G923 le 16 novembre 2026 : onze transitions
explicitement comptées, plus des transitions non quantifiées, sans oscillation
et avec un retour de force normal selon l'utilisateur. Réactivation et aller-retour
après redémarrage également vérifiés. Cela reste limité à la configuration testée.

La version 0.2.0 supprime l'exigence du SDK Logitech et conserve la correction.
**Aucun essai en jeu ni validation physique de la version 0.2.0 n'a encore eu lieu.**
Les autres volants et l'impact quantitatif sur les performances restent à vérifier.
Commencer les essais à force réduite, avec un moyen accessible d'interrompre les
effets. Comparer plusieurs transitions et vérifier direction, pédales, boutons
et retour de force normal, avec puis sans correction.
