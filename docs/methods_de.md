# Methoden — Archetypeninferenz aus aggregierten Gebäudestatistiken

Dieses Dokument beschreibt einen **praxisnahen methodischen Ansatz**, um aus **aggregierten statistischen Informationen** über einen Gebäudebestand eine **gewichtete bzw. gezählte Menge simulationsfähiger Gebäude-Archetypen** abzuleiten.  
Der Text richtet sich ausdrücklich auch an **Energie- und HVAC-Ingenieur:innen**, die wenig Erfahrung mit Statistik, Optimierung oder MILP-Methoden haben.

---

## 1. Grundidee und Gesamtprozess

ArcheInfer trennt den Modellierungsprozess bewusst in zwei klar abgegrenzte Schritte:

### 1) Archetypen-Inferenz (diese Bibliothek)
- Definition des **Archetypenraums**
- Formulierung von **Randbedingungen (Constraints)** aus Statistik
- Bestimmung von **Gewichten / Gebäudeanzahlen** je Archetyp
- Diagnose von Widersprüchen und Abweichungen

### 2) Gebäudesimulation (externe Werkzeuge)
- City Energy Analyst (CEA) oder internes Excel-Tool simulieren jeden Archetyp
- Simulationsergebnisse werden mit den Gewichten aggregiert

Diese Trennung ist typisch für **archetypenbasierte Gebäudebestandsmodelle**:  
Die Inferenz kümmert sich um *„Wie viele Gebäude welcher Art gibt es?“*,  
die Simulation um *„Wie viel Energie verbraucht ein Gebäude dieser Art?“*.

---

## 2. Datenmodell: Archetypen, Merkmale und Simulationsergebnisse

### 2.1 Archetypenraum: Kategorien + numerische Attribute

Wir betrachten eine endliche Menge von Archetypen, indexiert mit  
$i \in \{1,\dots,N\}$.

Jeder Archetyp ist durch einen **Merkmalsvektor** beschrieben:

#### Kategoriale Merkmale (Beispiele)
- $\text{nutzung} \in \{\text{Wohnen}, \text{Büro}, \text{Schule}, \dots\}$
- $\text{typologie} \in \{\text{EFH}, \text{MFH}, \dots\}$
- $\text{bauperiode} \in \{\text{<1945}, 1945\text{–}1980, \dots\}$
- $\text{heizsystem} \in \{\text{Kessel}, \text{WP}, \text{FW-Übergabe}, \dots\}$
- $\text{energieträger} \in \{\text{Gas}, \text{Strom}, \text{Biomasse}, \text{FW}, \dots\}$

#### Numerische Merkmale (Beispiele)
- $A_i$: Referenz-Nutzfläche des Archetyps $i$ in m²
- $d_i$: Anzahl Wohneinheiten pro Gebäude
- weitere numerische Attribute für Constraints oder Simulation

**Wichtig:**  
Nicht jede Kombination dieser Kategorien ist sinnvoll oder existent.  
Der Archetypenraum entsteht aus:
- einer **vorgegebenen Archetypenquelle**, und/oder
- einem **Generator mit Filterregeln**.

---

### 2.2 Simulationsergebnisse sind explizit nicht Teil der Inferenz

Jeder Archetyp besitzt einen extern berechneten Simulations-Outputvektor

$$
\mathbf{y}_i =
\begin{bmatrix}
\text{Heizwärme}_i \\
\text{Strom}_i \\
\text{Spitzenlast}_i \\
\vdots
\end{bmatrix}
$$

ArcheInfer berechnet $\mathbf{y}_i$ **nicht**.  
Aggregation erfolgt z. B. als:

- **Gebäudegewichtet**: 
$\mathbf{Y} = \sum_i w_i \, \mathbf{y}_i$

- **Flächengewichtet**:  $\mathbf{Y} = \sum_i w_i \, A_i \, \mathbf{y}_{i,\text{int}}$

---

## 3. Entscheidungsvariable

### A) Kontinuierliche Gewichte (LP)
- Variable: $w_i \ge 0$
- Interpretation: Anteil oder repräsentierte Gebäude

### B) Ganzzahlige Gebäudeanzahlen (MILP)
- Variable: $n_i \in \mathbb{Z}_{\ge 0}$
- Interpretation: tatsächliche Gebäudeanzahl

---

## 4. Formale Beschreibung von Constraints

### 4.1 Allgemeine Form

Ein Constraint $k$ wird über eine Aggregationsfunktion $g_k(i)$ definiert:

$$
G_k(\mathbf{w}) = \sum_i w_i \, g_k(i)
$$

Der Constraint ist dann z. B.:

- Gleichung: $G_k(\mathbf{w}) = b_k$
- Ungleichung: $G_k(\mathbf{w}) \le b_k$
- Weicher Constraint: Abweichung erlaubt, aber penalisiert

Typische Beispiele:
- $g(i) = 1$ (Gebäude zählen)
- $g(i) = A_i$ (Fläche)
- $g(i) = A_i \cdot \mathbb{1}_{\text{Gas}}(i)$
- $g(i) = \mathbb{1}_{\text{Periode}=p}(i)$

---

### 4.2 Typische Constraint-Arten

#### (1) Summen-Constraint

„Gesamte Wohnnutzfläche beträgt 12,3 Mio. m².“
$\sum_i w_i \, A_i \, \mathbb{1}_{\text{Wohnen}}(i) = 12.3 \times 10^6$

#### (2) Anteils-Constraint (Flächenanteil)

„**22 % der *beheizten Nutzfläche* werden mit Fernwärme versorgt.**“

Sei  
- $A_i$ die beheizte Nutzfläche des Archetyps $i$  
- $\mathbb{1}_{\text{FW}}(i)$ der Indikator, ob Archetyp $i$ Fernwärme nutzt  

Dann lautet der Constraint:

$$
\frac{\sum_{i} w_{i} A_{i}\,\mathbb{1}_{\text{FW}}(i)}
     {\sum_{i} w_{i} A_{i}}
= 0.22
$$

Zur Verwendung in einem linearen Solver wird dies äquivalent umgeformt zu:

$\sum_i w_i A_i \mathbf{1}_{\text{FW}}(i) - 0.22 \sum_i w_i A_i = 0$


#### (3) Randverteilungen
Für jede Bauperiode $p$:
$\sum_i w_i \mathbf{1}_{\text{Periode}=p}(i) = b_p$

#### (4) Kreuztabellen
Für Typologie $t$ und Energieträger $c$:

$\sum_i w_i A_i \mathbf{1}_{t,c}(i) = b_{t,c}$

---

## 5. Statistik → Archetypenraum (zentrales Mapping-Problem)

### 5.1 Crosswalks

Statistische Kategorien werden explizit auf Modellkategorien abgebildet:

$$
(\text{Stat-Kategorie}) \;\rightarrow\; \{\text{Prädikate auf } i\}
$$

Diese Abbildungen sind:
- explizit,
- versioniert,
- Teil der Modella
