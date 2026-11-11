# Disposable Targets

Tiers by the consequence of deleting. The locations were exercised on macOS; other systems list standard places only.

## Tier 1: regenerable caches (approve as a group)

Recreated on demand. The cost is time or bandwidth.

- **Xcode:** the contents of `~/Library/Developer/Xcode/DerivedData` and `iOS DeviceSupport`. A running IDE may hold a small folder; leftover megabytes are fine. `xcrun simctl delete unavailable` drops simulators without a runtime.
- **Package manager caches:** npm `~/.npm/_cacache`, bun `~/.bun/install/cache`, Gradle `~/.gradle/caches`, pip, uv (`uv cache clean`), CocoaPods, SwiftPM (`~/Library/Caches/org.swift.swiftpm`), the Cargo registry cache, Homebrew (`brew cleanup -s` or `~/Library/Caches/Homebrew`). Remove cache contents only, never the tool's binary or configuration; a bun install keeps its binary beside its cache.
- **Logs:** `~/Library/Logs`.
- **User temp:** entries of `$(getconf DARWIN_USER_TEMP_DIR)` untouched for 3 days or more (`find . -maxdepth 1 -mindepth 1 -mtime +3`). Leave newer entries; running tools may use them. Test runs often leave tens of GiB here.
- **Downloaded test browsers** (headless browser builds for automation) download again when needed.

## Tier 2: project build output (approve per project, list exact paths)

Run `scripts/scan_regenerable.py` over the folders that hold projects. Typical findings: `node_modules`, Rust, Maven or Gradle `target`, SwiftPM `.build`, `Pods`, `.venv`, `.turbo`, bytecode caches, project `DerivedData`.

- The cost is a reinstall or rebuild. A full Rust or Swift build of a large project can take long; say so for the largest ones.
- Custom names need a content check before they count as output. Derived-data copies with their own names contain `Build/`, `Index.noindex/` and `info.plist`. A folder called `build` may hold logs or agent state instead of compiler output.
- Generic names (`build`, `dist`, `out`, `.cache`) are `review`. Tracked by git means source: skip it. Ignored by git is a strong sign of output.
- The biggest share is usually copies of one project (worktrees, sandboxes), each with its own build output. Scan again after removing: what is left shows the next layer, and a depth cap in a search hides nested copies.

## Tier 3: user content (item by item, with size and regeneration cost)

- **Downloaded model files** (hub caches, speech and local-inference models): large, sometimes gated, slow to fetch again.
- **Xcode Archives:** symbols for crash reports and App Store resubmission.
- **Simulator runtimes:** `xcrun simctl runtime list`, then delete a named one. Fetching it again is several GiB.
- **Android virtual devices** (`~/.android/avd`), container and VM disk images, sandbox or guest home folders: application state may live there.
- **Whole projects, clones and worktrees:** see [worktrees.md](worktrees.md).
- **Trash:** emptying is irreversible, so the user does it or approves it. The terminal often cannot read it; see [accounting.md](accounting.md).
- **Installed apps and personal files** (Downloads, Pictures): list with sizes and leave the decision to the user.

## Never

Another user's files (report the permission error, do not escalate), system volumes, the target of a symlink, anything inside a `.git` directory, and anything outside the approved list.

## Other systems

Standard places, not exercised here: caches under `~/.cache`, package manager caches (`apt`, `dnf`), `journalctl --vacuum-size`, Windows temp and local-app caches. Container images and volumes are tier 3 because volumes can hold data.
