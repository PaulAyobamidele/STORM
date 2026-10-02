# STORM

**Behavioural conformance testing of web and mobile applications under real-world disruptions.**

STORM tests whether an application keeps its promises when things go wrong. You describe how the application should behave, including what it owes the user when a database write fails, a server stops answering or the app is killed mid-save. STORM then generates conformance tests from that description, injects the disruptions into the running application at the exact point each test calls for, and returns a verdict grounded in ioco theory.

This repository holds the STORM tool and the six case studies used to evaluate it.

## What STORM gives you

- **Disruptions as part of the specification.** Faults are gates of the behavioural model. The test generator places each fault where the test purpose asks, and the specification states what the user is owed afterwards.
- **Formal test generation.** Test cases come from the CADP toolbox and TESTOR under the ioco conformance relation. Every FAIL is an observed contradiction of the specification, not a heuristic.
- **Concrete tests, generated end to end.** The behavioural model and a System Interface model are composed before generation. Every test case therefore already contains the real UI steps (navigate, click, type, wait, observe), with no hand-written test scripts.
- **Verified fault injection.** Each disruption is injected through a declared mechanism (HTTP, shell, SQL, adb). A probe confirms it took effect, and it is restored after the run. A run whose fault could not be confirmed gets no verdict.
- **Honest verdicts.** PASS, FAIL or INCONCLUSIVE come from walking the test case. Silence is a FAIL only where the test case forbids it. A run the tester could not complete is reported separately as UNEXECUTABLE and is never counted as a verdict.
- **Web and Android.** Selenium drives web applications; Appium (UiAutomator2) drives Android applications.
- **Reusable templates.** A behaviour template and a System Interface template are instantiated per application with one command.

## How it works

```
 Behaviour model (LNT)        System Interface model (LNT)
 USER · APP · DATABASE ·      screens, concrete UI steps,
 DISRUPTOR, under SPEC        abstract gate last
            \                     /
             \___ SPEC || SI ____/          composed with CADP
                       |
           test purpose + .io file           which gates the tester controls
                       |
          TESTOR: complete test graph        one per purpose, under ioco
                       |
      extract_all: controllable test cases   concrete UI steps + fault gates
                       |
   Walker ── Selenium / Appium ── application under test
     │
     └── Disruption executor: inject, confirm, restore
                       |
     PASS · FAIL · INCONCLUSIVE   (UNEXECUTABLE = no verdict)
```

1. **Model the behaviour.** Write USER, APP, DATABASE and DISRUPTOR processes in LNT. A fault takes one of four shapes: interrupt, write-path, pre-armed or parameter.
2. **Model the interface.** The System Interface gives each abstract action its concrete UI steps.
3. **Compose and check.** `check_alphabet.py` verifies that the specification, interface, composition, purposes and configuration share one alphabet. CADP then builds SPEC ‖ SI.
4. **Generate.** For each test purpose, TESTOR builds the complete test graph and `extract_all` extracts its controllable test cases.
5. **Execute.** The walker runs each test case against the live application, hands fault gates to the disruption executor, and judges every observation against the test case.

## Repository layout

```
framework/
  concretization/      the execution engine
    algorithm.py         walker and verdict rules
    executors.py         Selenium (web) and Appium (Android) executors
    disruptor.py         disruption executor: inject, verify, restore
    fault_injector.py    Android fault injection over adb
    observation_oracle.py  checkpoint oracle driven by type_description.yml
    si_lnt_parser.py     System Interface parser
  scripts/             run.py (execute a test case), check_alphabet.py,
                       check_controllability.py, coverage_report.py,
                       classify_failure.py, eval_tables.py
  tests/               unit tests (pytest)
systems/
  template/            behaviour, interface, purpose and configuration templates
  <app>/               one directory per case study:
    model/               specification, System Interface, composition (LNT)
    test_purposes/       tp_*.lnt
    testor/              <app>.io, generate_tc_all.sh
    properties/          concrete_domain.yml, type_description.yml,
                         disruption_mapping.yml
    generated/tc/        generated test cases (.aut)
    RESULTS_campaign.md  campaign results and threats to validity
```

## Requirements

- Python 3.9 or later
- [CADP](https://cadp.inria.fr) with a licence, and TESTOR 3.8, available from its authors. These are needed for test generation only.
- Google Chrome, for web applications
- For Android applications: the Android SDK with an emulator, `adb`, Appium 2 with the UiAutomator2 driver, and the Python client: `pip install Appium-Python-Client`
- Docker, to run the web case studies locally

Install the Python dependencies:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install exrex Appium-Python-Client
```

Check the installation:

```sh
.venv/bin/python -m pytest framework/tests
```

## Quick start

**1. Create a new case study from the template.**

```sh
sh systems/template/new_system.sh myapp
```

This copies every template file into `systems/myapp/`, renames it, and prints the number of HOLE markers left to fill. `systems/myapp/notes/template_guide.md` explains each hole.

**2. Check the models agree.**

```sh
.venv/bin/python framework/scripts/check_alphabet.py systems/myapp
```

**3. Generate test cases** on the machine that holds the CADP licence:

```sh
cd systems/myapp/testor
sh generate_tc_all.sh
```

This writes the test cases to `generated/tc/variants/<purpose>/`, `model_size.txt` (size of the composed model) and `gen_times.tsv` (generation time per purpose).

**4. Execute a test case.** Web example:

```sh
.venv/bin/python framework/scripts/run.py \
  --aut systems/myapp/generated/tc/tc_nominal.aut \
  --platform html --url http://localhost:3000 \
  --system-interface   systems/myapp/model/system_interface_myapp.lnt \
  --concrete-domain    systems/myapp/properties/concrete_domain.yml \
  --type-description   systems/myapp/properties/type_description.yml \
  --disruption-mapping systems/myapp/properties/disruption_mapping.yml \
  --timeout 10 --report
```

Use `--platform android` for an Android application. The command prints the verdict. The exit code is 2 when the run was UNEXECUTABLE.

**5. Tabulate a campaign.**

```sh
.venv/bin/python framework/scripts/eval_tables.py systems/myapp --latex
```

## Case studies

| Application | Platform | Domain | What is modelled | Results |
|---|---|---|---|---|
| [FoodYou](https://github.com/maksimowiczm/FoodYou) | Android | Nutrition | Searching foods, logging and removing diary entries, the daily calorie total | [systems/foodyou](systems/foodyou/RESULTS_campaign.md) |
| [MedTimer](https://github.com/Futsch1/medTimer) | Android | Health | Creating medicines, marking doses taken or skipped, correcting and deleting dose records, pill stock | [systems/medtimer](systems/medtimer/RESULTS_campaign.md) |
| [SimpleBaby](https://github.com/adulbrich/SimpleBaby) | Android | Childcare | Logging and deleting feedings, the feeding history, manual sleep entries, the sleep stopwatch | [systems/simplebaby](systems/simplebaby/RESULTS_table.tex) |
| [Spliit](https://github.com/spliit-app/spliit) | Web | Finance | Creating, viewing and deleting group expenses, the group total, the activity log | [systems/spliit](systems/spliit/RESULTS_campaign.md) |
| [Moodle](https://github.com/moodle/moodle) | Web | Education | Quiz attempts, assignment submission and grading | [systems/moodle](systems/moodle) |
| [Mastodon](https://github.com/mastodon/mastodon) | Web | Social networking | Publishing and deleting posts, the home timeline and profile, the post count | [systems/mastodon](systems/mastodon/RESULTS_campaign.md) |

Disruptions are organised by the layer they strike:

| Layer | Examples |
|---|---|
| User | app killed or page left mid-write, expired session, lost connection |
| Application | silently rejected write, unresponsive server, stale cache, failing external service, delayed background processing |
| Database | aborted transaction, corrupted record, lost event |
| Infrastructure | database or background worker down, full or failing storage |
| Input | invalid or over-limit values |

Every campaign's results file records the commands, logs and inputs needed to regenerate its numbers. The [Mastodon campaign](systems/mastodon/RESULTS_campaign.md) is a complete example: 16 test purposes, 31 test cases, every number regenerable from the files in its directory.

## Setting up the case studies

The applications under test are not part of this repository. Each is cloned at the exact commit the campaigns ran against, into `systems/<app>/sut/`. Our changes to an application's build or deployment are in `systems/<app>/setup/`. You only need an application to **execute** test cases: generating them needs only the models in this repository.

| Application | Repository | Version / commit | Platform |
|---|---|---|---|
| FoodYou | https://github.com/maksimowiczm/FoodYou | 3.4.8, `35ab8f1e9ad54194dbc9521fe89d752c913d3cae` | Android emulator, Appium |
| MedTimer | https://github.com/Futsch1/medTimer | `abd19508809d0501b59dbf175ca4241d1999b392` | Android emulator, Appium |
| SimpleBaby | https://github.com/adulbrich/SimpleBaby | `a46e3cf2939e00f7b4b966b87f5e0694fa42fdb9` | Android emulator, Appium, local Supabase |
| Spliit | https://github.com/spliit-app/spliit | 1.19.1, `d3b151e1506f26fd582c30b09427606cc2fe7826` | Docker, Chrome |
| Moodle | https://github.com/moodle/moodle with https://github.com/moodlehq/moodle-docker | v4.5.12, `b9315ff5cb42e11b40c972f3f7194ba8b0c0bbf8`; moodle-docker `81a20665c2d2322469dc491c1f972ebde90ec014` | Docker, Chrome |
| Mastodon | https://github.com/mastodon/mastodon | v4.7.2, `3987b9fd624010eeeaeb7cad96606b05aa813f6a` | Docker, Chrome |

Clone any of them the same way, run from the repository root. FoodYou is shown here:

```sh
git clone https://github.com/maksimowiczm/FoodYou.git systems/foodyou/sut/foodyou
git -C systems/foodyou/sut/foodyou checkout 35ab8f1e9ad54194dbc9521fe89d752c913d3cae
```

Every case study has a seed script that resets the application to a clean, verified state before each test case, and a sweep script that walks every generated test case of a purpose. Read each script's header before running it.

### Android applications (FoodYou, MedTimer, SimpleBaby)

You need the Android SDK (command-line tools), JDK 21, an Android emulator image that allows `adb root`, and an Appium 2 server with the UiAutomator2 driver. Each case study's `env.sh` puts `adb` on the `PATH`, names the device and the Appium port, and reports what is running. Source it in the same shell that runs the tests.

**FoodYou**

```sh
cd systems/foodyou/sut/foodyou && ./gradlew app:assembleDebug && cd -
source systems/foodyou/env.sh
bash systems/foodyou/boot_emulator.sh
bash systems/foodyou/check_env.sh
bash systems/foodyou/run_variants.sh happy
```

Install the debug APK the build produces on the emulator with `adb install`. `boot_emulator.sh` starts the emulator with working DNS, because a searchable food database requires internet access. `check_env.sh` refuses to run if the device cannot reach it.

**MedTimer**

```sh
cd systems/medtimer/sut/medtimer && ./gradlew app:assembleDebug && cd -
source systems/medtimer/env.sh
sh systems/medtimer/seed.sh
bash systems/medtimer/run_variants.sh nominal
```

Install `MedTimer-foss-debug.apk` from the build output with `adb install`. `seed.sh` clears the app's data and grants the notification permission. The walk itself creates the fixture.

**SimpleBaby**

SimpleBaby needs a local Supabase backend (Supabase CLI and Docker) and runs as a release build.

```sh
cd systems/simplebaby/sut/simplebaby
git apply ../../setup/simplebaby.patch
npm install
supabase start
npx expo prebuild --platform android
cd -
source systems/simplebaby/env.sh
bash systems/simplebaby/check_env.sh
sh systems/simplebaby/seed.sh
bash systems/simplebaby/run_variants.sh nominal_signed
```

Before you run it, complete these configuration steps:

- **Backend address.** Create `systems/simplebaby/sut/simplebaby/.env` with `EXPO_PUBLIC_SUPABASE_URL=http://10.0.2.2:54321` and `EXPO_PUBLIC_SUPABASE_KEY` set to the anon key that `supabase start` prints.
- **Plain HTTP.** Because the local backend is plain HTTP, set `android:usesCleartextTraffic="true"` in the generated `android/app/src/main/AndroidManifest.xml`.
- **Release APK.** Build the release APK from `android/` and install it.
- **Separate emulator.** The case study uses emulator `emulator-5556`, so it never collides with the other Android apps.

`check_env.sh` refuses a sweep unless the device, root access, the release build, Appium and Supabase are all in place.

### Web applications (Spliit, Moodle, Mastodon)

You need Docker and Google Chrome.

**Spliit**

```sh
cd systems/spliit/sut/spliit
git apply ../../setup/spliit.patch
npm install --package-lock-only
cp container.env.example container.env
docker compose up -d
cd -
.venv/bin/python systems/spliit/setup/fault_middleware.py &
bash systems/spliit/run_variants.sh nominal
```

The patch pins PostgreSQL 17 and fixes the image build. `fault_middleware.py` is a proxy on port 3002 in front of Spliit on port 3000, through which application faults are injected. STORM drives `http://localhost:3002`. The `app_extapi_fail` purpose also needs the currency service redirected:

```sh
sudo sh -c "echo '127.0.0.1 api.frankfurter.app' >> /etc/hosts"
```

**Moodle**

```sh
export MOODLE_DOCKER_WWWROOT="$PWD/systems/moodle/sut/moodle"
export MOODLE_DOCKER_DB=pgsql
export MOODLE_DOCKER_WEB_PORT=8080
cp systems/moodle/sut/moodle-docker/config.docker-template.php systems/moodle/sut/moodle/config.php
cd systems/moodle/sut/moodle-docker
bin/moodle-docker-compose up -d
bin/moodle-docker-wait-for-db
bin/moodle-docker-compose exec webserver php admin/cli/install_database.php --agree-license --fullname="STORM" --shortname="storm" --adminpass="test" --adminemail="admin@example.com"
bin/moodle-docker-compose exec -T webserver php /dev/stdin < ../../seed_moodle.php
cd -
bash systems/moodle/run_variants.sh happy
```

`seed_moodle.php` creates the course, users, quiz and assignment the models refer to. Before every test case, `reset_moodle.php` clears any fault left behind and restores the fixture.

**Mastodon**

```sh
cd systems/mastodon/sut/mastodon
cp ../../setup/docker-compose.override.yml ../../setup/Caddyfile .
cp .env.production.sample .env.production
```

In `.env.production`, set `LOCAL_DOMAIN=mastodon.localhost` and `DEFAULT_LOCALE=en`, and generate the secrets as described in Mastodon's documentation. Then:

```sh
docker compose run --rm web bundle exec rails db:setup
docker compose up -d
docker compose exec web bin/tootctl accounts create bob --email bob@mastodon.localhost --confirmed --approve
cd -
export MASTODON_PW='<password tootctl printed>'
sh systems/mastodon/seed.sh
sh systems/mastodon/run_suite.sh mycampaign
```

The override moves Mastodon's ports out of the way and adds a Caddy proxy that serves `https://mastodon.localhost` with a local certificate, because Mastodon's production mode requires HTTPS. The browser accepts that certificate. `seed.sh` clears every fault, removes bob's posts, and verifies the clean state before each case.

## Verdicts

| Outcome | Meaning |
|---|---|
| PASS | The test case reached its `:PASS:` state and every checkpoint matched the specification. |
| FAIL | The application contradicted the specification: a wrong observed value, or no output where the test case forbids silence. |
| INCONCLUSIVE | The application behaved correctly, but the test purpose could not be reached, or silence was permitted at that point. |
| UNEXECUTABLE | Not a verdict. The tester could not carry out the run: a fault not confirmed, a step that could not be applied, a dead end. Fix the cause and run again. |

## Citation

If you use STORM, please cite:

```bibtex
@inproceedings{storm2027,
  title     = {{STORM}: Behavioural Conformance Testing Under Real-World Disruptions},
  author    = {TBD},
  booktitle = {Proceedings of the 49th IEEE/ACM International Conference on Software Engineering (ICSE)},
  year      = {2027}
}
```

## Acknowledgements

STORM builds on [CADP](https://cadp.inria.fr) and TESTOR (Marsso, Mateescu and Serwe, "TESTOR: A Modular Tool for On-the-Fly Conformance Test Case Generation", TACAS 2018).
