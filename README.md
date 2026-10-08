# Steve in MGR:R

Block Raiden is a Steve character mod for the Steam PC version of **Metal Gear Rising: Revengeance**. It adds a voxel diamond sword and a Minecraft shield attached to the left forearm.

**NOT AN OFFICIAL MINECRAFT PRODUCT. NOT APPROVED BY OR ASSOCIATED WITH MOJANG OR MICROSOFT.** Not affiliated with Konami or PlatinumGames.

## Download and install

[**Download Block Raiden 0.1.0 alpha — Windows ZIP, 19.5 MB**](https://github.com/warshock1181/Steve-in-MGR-R/raw/refs/heads/main/downloads/Block-Raiden-0.1.0-alpha.zip)

1. Install your own Steam PC copy of Rising and Minecraft Java **1.21.11**. Run that Minecraft version once through your launcher to install its client JAR.
2. Extract the entire ZIP into a normal folder, then close Rising.
3. Double-click **Install.cmd**. The installer searches Steam libraries and the usual Minecraft Java folder; it asks for custom paths if needed.
4. Wait for “Installed and verified 26 files,” then use **Play.cmd** or launch Rising through Steam.
5. Use the default Raiden costume and standard HF Blade for the main story.

The ZIP includes its own portable runtime for Windows 10/11 on x86-64 PCs. You do not need to install Python or Blender. Recipients supply their own installed game assets; the package does not contain original game archives, Minecraft texture files, saves, or personal backups. A Bedrock-only Minecraft installation does not supply the required Java textures. Unsupported game asset versions are rejected before installation.

[ZIP checksum](downloads/Block-Raiden-0.1.0-alpha.zip.sha256) · [Package validation](VALIDATION.txt)

## Features and current limits

- Steve replaces the prologue, default cyborg, story suit, and Mariachi playable bodies.
- A voxel diamond sword replaces the prologue/standard blade and final Murasama.
- The forearm shield follows Rising’s original guard/parry animation. Use the normal parry input: push toward an incoming attack and press light attack at the correct time.
- Original movement, attacks, Blade Mode, upgrades, health, enemies, and checkpoints remain in use.
- The shield has no separate hold button or independent collision system. Story removal of the left arm also removes the shield.
- Block building is not included. Other optional costumes and weapons retain their original appearance.
- **Prerecorded cutscenes, portraits, artwork, voices, and character names still show or refer to Raiden.**

**This is an alpha release. A complete campaign playthrough, successful live sword hits, and successful live shield parries remain unverified.** The character was observed in the opening R-00 battle, and its structure and shield orientation were checked. Automated combat inputs were unreliable, so the release is not claimed to be fully verified for the campaign.

## Verify and uninstall

**Verify.cmd** checks all 26 installed file hashes. Close the game and use **Uninstall.cmd** to restore backed-up loose files and remove this mod’s new files. Uninstall stops before changing anything if a later mod has altered a target file.

The installer writes only loose files under `GameData/pl`. It leaves the executable, CPK archives, movies, and saves intact. Backups are stored under `%LOCALAPPDATA%\BlockRaidenMod\<game-folder-id>`. Keep these backups. Recover an interrupted operation with **Uninstall.cmd**, then install again if desired.

Custom paths can be supplied from a command prompt in the extracted package:

```bat
Install.cmd --game-dir "E:\Games\METAL GEAR RISING REVENGEANCE" --minecraft-jar "E:\Minecraft\versions\1.21.11\1.21.11.jar"
Uninstall.cmd --game-dir "E:\Games\METAL GEAR RISING REVENGEANCE"
```

## Source

This repository contains the portable installer source in `scripts`, seven copy/literal model patches in `patches`, and the verified release manifest. The downloadable ZIP additionally includes licensed CPython and Pillow runtime components. Original model data is read from the recipient’s Rising archives, and textures are rebuilt from the recipient’s Minecraft client.

To run the source directly, install Python 3.14 on Windows and the pinned dependency:

```bat
python -m pip install -r requirements.txt
python scripts\mod_manager.py install
python scripts\mod_manager.py verify
python scripts\mod_manager.py uninstall
```

A build-only command produces the verified loose mod files in a chosen output folder without installing them:

```bat
python scripts\mod_manager.py build --game-dir "E:\Games\METAL GEAR RISING REVENGEANCE" --minecraft-jar "E:\Minecraft\versions\1.21.11\1.21.11.jar" --output "build\mod"
```

Reconstruction reproduced all 26 local mod files byte for byte. Isolated checks passed for installation, reinstallation, backups, conflict refusal, rollback after a simulated write failure, and interruption recovery. The extracted ZIP also rebuilt the same files from a relocated folder.

Share the original ZIP, rather than generated game files or installation backups. Do not sell this fan mod or present it as official. [Original-code license](LICENSE.txt) · [Runtime notices](THIRD-PARTY-NOTICES.txt) · [Dependency versions and hashes](DEPENDENCIES.json)

The models were created using the [MGR2Blender2MGR workflow](https://github.com/Gaming-With-Portals/MGR2Blender2MGR); the Blender add-on is not bundled. The portable installer uses its own minimal archive and patch readers. [CRILAYLA format reference](https://github.com/kamikat/cpktools/blob/master/cpk/crilayla.py). Minecraft assets remain subject to the [Minecraft EULA](https://www.minecraft.net/en-us/eula) and [usage guidelines](https://www.minecraft.net/en-us/usage-guidelines).

For support or bug reports, [open an issue](https://github.com/warshock1181/Steve-in-MGR-R/issues). Include your game version, costume, chapter, and the installer error if relevant.
