# ADR — WeasyPrint en extra optionnel `[pdf]`, génération PDF Linux/Docker uniquement

**Contexte.** `pyproject.toml` déclarait `weasyprint` comme dépendance de base du
backend. Installer le backend en dehors de Docker (venv local d'un poste de
développement Windows, par exemple) échoue à l'exécution : WeasyPrint dépend de
bibliothèques natives (Pango, Cairo, GDK-Pixbuf, HarfBuzz, Fribidi) qui ne sont
pas présentes par défaut hors d'un environnement Linux, et leur installation
manuelle sous Windows est lourde et non reproductible. Résultat : `import
weasyprint` lève une `OSError` (`cannot load library 'libgobject-2.0-0'`) dès que
le paquet est importé, même pour un développeur qui ne touche pas au module
`rapports`.

**Décision.** `weasyprint` passe dans un extra optionnel `pdf` de
`pyproject.toml` (`pip install -e ".[dev,pdf]"`). L'image Docker du backend
(Debian bookworm, via `python:3.12-slim`) installe cet extra ainsi que les
bibliothèques système nécessaires (`libpango-1.0-0`, `libpangocairo-1.0-0`,
`libpangoft2-1.0-0`, `libgdk-pixbuf-2.0-0`, `libharfbuzz0b`, `libfribidi0`,
`fonts-dejavu-core`, `fonts-noto-core`) — c'est le seul environnement où la
génération de PDF est censée fonctionner ou être testée. `backend/app/modules/
rapports/pdf.py` (étape 9 de la roadmap) devra importer `weasyprint` en
paresseux, à l'intérieur de la fonction qui génère le PDF, jamais au niveau du
module : ainsi, importer `app.modules.rapports` (schémas, service, router) ne
plante pas hors Docker, seul l'appel effectif à la génération de PDF l'exige.

**Conséquences.** Un développeur qui installe le backend sans l'extra `pdf` peut
travailler sur n'importe quel module sauf `rapports/pdf.py` sans friction.
`make lint` et `make test` en local n'ont plus besoin du runtime GTK. Le prix :
`rapports/pdf.py` ne pourra être testé unitairement (au sens strict, sans
mock) que dans un conteneur Linux ou en CI configurée avec les mêmes paquets
système — à documenter dans les tests de l'étape 9 le moment venu.
