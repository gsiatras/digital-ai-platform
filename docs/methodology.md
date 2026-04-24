# Μεθοδολογία Πλατφόρμας — Τεχνική & Ακαδημαϊκή Τεκμηρίωση

> Αυτό το αρχείο καταγράφει τις τεχνικές επιλογές, τους μαθηματικούς τύπους και τις ακαδημαϊκές αναφορές για κάθε βασικό μηχανισμό της πλατφόρμας. Συντηρείται παράλληλα με τον κώδικα.

---

## 1. Παρακολούθηση Ενεργειακής Κατανάλωσης

### 1.1 Κίνητρο

Η αποδοτική χρήση ενέργειας αποτελεί κεντρικό ζήτημα στην κλίμακα των σύγχρονων υπολογιστικών υποδομών. Έρευνες έχουν δείξει ότι η εκπαίδευση και η εκτέλεση μεγάλων νευρωνικών δικτύων μπορεί να έχει σημαντικό περιβαλλοντικό αποτύπωμα [Strubell et al., 2019; Patterson et al., 2021]. Στο πλαίσιο αυτής της πτυχιακής, στόχος είναι ο έξυπνος προγραμματισμός εργασιών inference (προβολής) σε κόμβους υπολογιστικού cluster, με κριτήριο τόσο την απόδοση όσο και την ενεργειακή αποδοτικότητα.

### 1.2 RAPL — Running Average Power Limit

**Τι είναι:** Το RAPL (Running Average Power Limit) είναι ένας μηχανισμός που παρέχουν οι επεξεργαστές Intel και AMD για μέτρηση και έλεγχο της κατανάλωσης ενέργειας σε επίπεδο hardware. Εκθέτει δεδομένα μέσω Model Specific Registers (MSR) και, σε νεότερους πυρήνες Linux, μέσω του υποσυστήματος `powercap` στο `/sys/class/powercap/intel-rapl/`.

**Γιατί το εξετάσαμε:** Το RAPL παρέχει πραγματικές μετρήσεις ενέργειας σε επίπεδο CPU package, core και DRAM, χωρίς ανάγκη για εξωτερικό hardware [Khan et al., 2018]. Είναι η πιο ακριβής μέθοδος λογισμικού για μέτρηση κατανάλωσης σε x86 συστήματα.

**Γιατί δεν λειτούργησε στη συγκεκριμένη υλοποίηση:**

Το περιβάλλον ανάπτυξης χρησιμοποιεί **minikube με Docker driver**: κάθε Kubernetes κόμβος είναι ένα Docker container που τρέχει στον host. Αν και το αρχείο `/sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj` ήταν προσβάσιμο εντός των containers (bind mount του host `/sys`), ο μετρητής ενέργειας παρέμενε **στατικός** — δεν ενημερωνόταν κατά τη διάρκεια υπολογισμών. Αυτό επιβεβαιώθηκε πειραματικά: δύο διαδοχικές αναγνώσεις με ενδιάμεσο χρόνο 10 δευτερολέπτων (κατά τη διάρκεια inference) επέστρεφαν πανομοιότυπη τιμή.

Η αιτία είναι γνωστός περιορισμός: ο πυρήνας Linux ενημερώνει τους RAPL μετρητές στο sysfs από το context του host kernel, αλλά αυτές οι ενημερώσεις δεν αντικατοπτρίζονται αξιόπιστα μέσα σε Docker containers σε περιβάλλοντα χωρίς πλήρη πρόσβαση MSR. Αντίστοιχο πρόβλημα αναφέρεται σε VM-based περιβάλλοντα [Hackenberg et al., 2013].

---

### 1.3 Kepler & eBPF — Η Επιλεγμένη Προσέγγιση

**Τι είναι το Kepler:** Το Kepler (Kubernetes Efficient Power Level Exporter) είναι ένα open-source εργαλείο της CNCF που χρησιμοποιεί **eBPF** (extended Berkeley Packet Filter) για να παρακολουθεί την κατανάλωση CPU ανά container σε επίπεδο kernel, και εκθέτει μετρήσεις μέσω Prometheus endpoint. Αναπτύχθηκε από το Sustainable Computing IO project.

**Τι είναι το eBPF:** Το eBPF επιτρέπει την εκτέλεση προγραμμάτων απευθείας στον πυρήνα του Linux, συνδεδεμένων σε kernel events (π.χ. context switches, system calls), χωρίς τροποποίηση του kernel κώδικα. Το Kepler χρησιμοποιεί eBPF probes για να μετράει τον **πραγματικό χρόνο CPU** που καταναλώνει κάθε container (cgroup), ανεξάρτητα από το είδος της φόρτωσης.

**Γιατί το eBPF λειτούργησε:** Σε αντίθεση με το RAPL, το eBPF λειτουργεί στο kernel namespace του host (το Kepler pod τρέχει με `privileged: true` και `hostNetwork: true`), οπότε παρακολουθεί context switches και CPU time των container processes απευθείας από τον host kernel. Αυτό επιβεβαιώθηκε: ο μετρητής `kepler_container_bpf_cpu_time_ms_total` αυξήθηκε σωστά κατά τη διάρκεια inference.

**Αρχιτεκτονική στην πλατφόρμα:**

- Το Kepler αναπτύχθηκε ως **DaemonSet** (ένα pod ανά Kubernetes κόμβο)
- Χρησιμοποιεί `hostNetwork: true` και `hostPort: 9102`, άρα κάθε κόμβος εκθέτει το endpoint `NODE_IP:9102/metrics`
- Ο manager service γνωρίζει τη στατική αντιστοίχιση worker → node IP και κάνει scrape το αντίστοιχο Kepler pod
- Δεν απαιτείται Prometheus ή Grafana — το scraping γίνεται απευθείας από Python με `requests`

---

### 1.4 Μοντέλο Ισχύος — Γραμμικό Μοντέλο Ενέργειας

#### Θεωρητικό υπόβαθρο

Το **γραμμικό μοντέλο ισχύος** βασίζεται στην έννοια της **ενεργειακά αναλογικής υπολογιστικής** (energy-proportional computing), που εισήγαγαν οι Barroso & Hölzle (2007). Η βασική παρατήρηση: η κατανάλωση ισχύος ενός επεξεργαστή είναι κατά προσέγγιση γραμμική συνάρτηση της χρησιμοποίησης (utilization):

$$P(u) = P_{\text{idle}} + (P_{\text{max}} - P_{\text{idle}}) \cdot u$$

όπου:
- $P(u)$: στιγμιαία κατανάλωση ισχύος (Watt)
- $P_{\text{idle}}$: κατανάλωση σε αδράνεια (Watt)
- $P_{\text{max}}$: μέγιστη κατανάλωση = TDP (Thermal Design Power, Watt)
- $u \in [0, 1]$: χρησιμοποίηση CPU

#### Προσαρμογή για eBPF CPU Time

Επειδή το Kepler παρέχει **πραγματικό χρόνο εκτέλεσης CPU ανά container** (όχι ποσοστό χρησιμοποίησης), χρησιμοποιούμε τον παρακάτω τύπο:

$$E_{\text{job}} = \frac{\Delta t_{\text{cpu}}}{1000} \cdot P_{\text{core}}$$

όπου:
- $E_{\text{job}}$: ενέργεια που καταναλώθηκε για το συγκεκριμένο job (Joule)
- $\Delta t_{\text{cpu}}$: διαφορά του `kepler_container_bpf_cpu_time_ms_total` πριν και μετά το inference (milliseconds)
- $P_{\text{core}} = \frac{\text{TDP}}{N_{\text{cores}}}$: εκτιμώμενη ισχύς ανά core σε πλήρη φόρτο (Watt)

#### Παράμετροι για τον AMD Ryzen 7 9800X3D

| Παράμετρος | Τιμή |
|---|---|
| TDP | 120 W |
| Φυσικοί πυρήνες | 8 |
| $P_{\text{core}}$ | 15 W |

#### Γιατί αυτή η προσέγγιση είναι έγκυρη

1. **Ανά-container απόδοση ενέργειας:** Το eBPF παρακολουθεί το CPU time ανά cgroup, που αντιστοιχεί ακριβώς στο container. Αντίθετα, το psutil δίνει ολική χρησιμοποίηση συστήματος — δεν διαχωρίζει containers.

2. **Συντηρητική εκτίμηση:** Υποθέτουμε ότι κατά τον ενεργό υπολογισμό, ο πυρήνας τρέχει σε πλήρη TDP ($u \approx 1$). Αυτό είναι συντηρητικό (υπερεκτίμηση) αλλά συνεπές.

3. **Αναλογική κατανομή:** Ο τύπος βασίζεται στην αρχή της αναλογικής κατανομής ενέργειας (ratio-based attribution), που χρησιμοποιείται και από το Kepler εσωτερικά όταν δεν είναι διαθέσιμο RAPL [Kepler documentation, 2023].

---

### 1.5 Μοντέλο Εκπομπών Άνθρακα

#### Τύπος

$$C_{\text{job}} = \frac{E_{\text{job}}}{3{,}600{,}000} \cdot I_{\text{node}}$$

όπου:
- $C_{\text{job}}$: εκπομπές $\text{CO}_2$ (gram)
- $E_{\text{job}}$: ενέργεια (Joule) — $3{,}600{,}000 \, \text{J} = 1 \, \text{kWh}$
- $I_{\text{node}}$: ένταση άνθρακα του δικτύου ηλεκτρισμού του κόμβου ($\text{gCO}_2/\text{kWh}$)

#### Προσομοιωμένες τιμές ανά κόμβο

Οι τιμές έντασης άνθρακα δεν είναι πραγματικές για την τοποθεσία του cluster (όλοι οι κόμβοι τρέχουν στο ίδιο μηχάνημα), αλλά **προσομοιώνουν ετερογενές περιβάλλον** όπου οι κόμβοι βρίσκονται σε διαφορετικές γεωγραφικές περιοχές με διαφορετικά ενεργειακά μίγματα:

| Κόμβος | Προσομοιωμένη Περιοχή | $I$ (gCO₂/kWh) |
|---|---|---|
| Worker A | Μέσος Ευρωπαϊκός κόμβος (EU average) | 350 |
| Worker B | Κόμβος εξαρτώμενος από άνθρακα (π.χ. Πολωνία) | 600 |
| Worker C | Κόμβος ανανεώσιμων πηγών (π.χ. Νορβηγία) | 100 |

**Ακαδημαϊκή τεκμηρίωση:** Οι τιμές αυτές είναι εντός των πραγματικών εύρων που καταγράφει η πλατφόρμα ElectricityMaps (πρώην ElectricityMap) για χώρες της Ευρώπης [IEA, 2023; ElectricityMaps, 2024]. Η μεθοδολογία προσομοίωσης ετερογενούς ενεργειακού μίγματος είναι ευρέως αποδεκτή σε ερευνητικά συστήματα carbon-aware scheduling [Wiesner et al., 2022; Radovanović et al., 2022].

---

## 2. DQN Agent — Έξυπνος Προγραμματισμός Εργασιών

*(Προς συμπλήρωση)*

### 2.1 Κίνητρο

Ο στόχος είναι η αντικατάσταση του απλού round-robin scheduling με έναν **DQN (Deep Q-Network) agent** που μαθαίνει να κατανέμει εργασίες inference στους κόμβους με βάση την ενεργειακή αποδοτικότητα και την εκπομπή άνθρακα, σε σχέση με τη βασική γραμμή (round-robin).

### 2.2 Διάνυσμα Κατάστασης (State Vector)

$$s_t = [\text{time\_of\_day},\ u_A,\ u_B,\ u_C,\ I_A,\ I_B,\ I_C,\ q_A,\ q_B,\ q_C,\ p_{\text{job}}]$$

| Στοιχείο | Περιγραφή |
|---|---|
| $\text{time\_of\_day}$ | Ώρα ημέρας (0–1 normalized) |
| $u_A, u_B, u_C$ | CPU utilization κόμβων A, B, C |
| $I_A, I_B, I_C$ | Ένταση άνθρακα κόμβων (gCO₂/kWh) |
| $q_A, q_B, q_C$ | Μήκος ουράς εργασιών ανά κόμβο |
| $p_{\text{job}}$ | Προτεραιότητα εργασίας |

### 2.3 Χώρος Ενεργειών

| Action | Περιγραφή |
|---|---|
| 0 | Ανάθεση στον κόμβο A |
| 1 | Ανάθεση στον κόμβο B |
| 2 | Ανάθεση στον κόμβο C |
| 3 | Καθυστέρηση (delay) |
| 4 | Απόρριψη (skip) |

### 2.4 Συνάρτηση Ανταμοιβής (Reward)

*(Προς ορισμό)*

---

## 3. Βιβλιογραφία

1. **Barroso, L. A., & Hölzle, U. (2007).** The Case for Energy-Proportional Computing. *IEEE Computer*, 40(12), 33–37. https://doi.org/10.1109/MC.2007.443

2. **Strubell, E., Ganesh, A., & McCallum, A. (2019).** Energy and Policy Considerations for Deep Learning in NLP. *Proceedings of ACL 2019*. https://doi.org/10.18653/v1/P19-1355

3. **Patterson, D., et al. (2021).** Carbon Emissions and Large Neural Network Training. *arXiv:2104.10350*. https://arxiv.org/abs/2104.10350

4. **Khan, K. N., et al. (2018).** RAPL in Action: Experiences in Using RAPL for Power Measurements. *ACM Transactions on Modeling and Performance Evaluation of Computing Systems*, 3(2), 1–26. https://doi.org/10.1145/3177754

5. **Hackenberg, D., et al. (2013).** An Introduction to the HALO Power Measurement Infrastructure. *IEEE International Symposium on Workload Characterization*. — *[Αναφορά για περιορισμούς RAPL σε VM/container περιβάλλοντα]*

6. **Wiesner, P., et al. (2022).** Let's Wait Awhile: How Temporal Workload Shifting Can Reduce Carbon Emissions in the Cloud. *Proceedings of the 23rd ACM/IFIP Middleware Conference*. https://doi.org/10.1145/3528535.3531517

7. **Radovanović, A., et al. (2022).** Carbon-Aware Computing for Datacenters. *IEEE Transactions on Power Systems*, 38(2), 1270–1280. https://doi.org/10.1109/TPWRS.2022.3173250

8. **Lannelongue, L., Grealey, J., & Inouye, M. (2021).** Green Algorithms: Quantifying the Carbon Footprint of Computation. *Advanced Science*, 8(12), 2100707. https://doi.org/10.1002/advs.202100707

9. **Sustainable Computing IO — Kepler Project (2023).** Kepler: Kubernetes-based Efficient Power Level Exporter. GitHub: https://github.com/sustainable-computing-io/kepler

10. **IEA (2023).** *Electricity 2023 — Analysis and Forecast to 2025*. International Energy Agency. https://www.iea.org/reports/electricity-2023

11. **ElectricityMaps (2024).** Real-time Carbon Intensity Data. https://www.electricitymaps.com
