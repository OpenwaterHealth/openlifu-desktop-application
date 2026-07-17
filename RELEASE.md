# openlifu-app Release Process

This document describes our release process for the OpenLIFU desktop application.

## Versioning

The desktop application version is defined in:

```text
Applications/OpenLIFUApp/slicer-application-properties.cmake
```

Use Git tags of the form:

```text
vX.Y.Z
vX.Y.Z-rc.N
```

`VERSION_MAJOR`, `VERSION_MINOR`, and `VERSION_PATCH` are numeric. Do not put
`-rc.N` or other suffixes in those fields. A release candidate is identified by
the Git tag, GitHub prerelease, release component version table row, and package
filenames.

To visibly distinguish release candidates inside the running application,
temporarily add an
`APPLICATION_DISPLAY_NAME` in
`Applications/OpenLIFUApp/slicer-application-properties.cmake`. For example,
`v1.12.0-rc.2` could use:

```cmake
set(APPLICATION_DISPLAY_NAME
  "OpenLIFU (RC 2)"
  )
```

Remove release-candidate display-name decorations before the final release.

Use a new minor version for a planned desktop application release and a patch
version for fixes to an already released line.

## Branch Model

`main` is the development branch. Release branches are stabilization branches:

```text
main
release/1.13
  v1.13.0-rc.1
  v1.13.0-rc.2
  v1.13.0
  v1.13.1
```

After a release branch is cut, new feature work continues on `main`. The release
branch is primarily for stabilization fixes, release-specific updates, and
SlicerOpenLIFU updates from the selected release line that are needed for the
desktop application release.

## Planned Cadence

We plan for a biannual desktop application release cadence with an 8-week stabilization window:

```text
T-8 weeks: dependency-line freeze and release branch
T-6 weeks: first release candidate
T-4 weeks: second release candidate, if needed
T-2 weeks: release-blocker-only changes
T: final release
```

The dependency-line freeze means choosing the Slicer version and the
SlicerOpenLIFU release line (with the `openlifu` compatibility line following from that).
It does not require freezing the exact SlicerOpenLIFU tag for the whole
stabilization period. So in other words the major and minor SlicerOpenLIFU versions are frozen,
but there is room for incorporating bug fixes after the freeze by updating the
SlicerOpenLIFU patch version.

## Package Python Environment Metadata

For every release candidate, final release, and patch release, inspect the
packaged `share/OpenLIFU-<Slicer version>/BuildMetadata` directory. Confirm that
`python-environment.txt` and `python-environment.cdx.json` contain the expected
`openlifu` version. Investigate any CycloneDX warning before publishing; the
package build intentionally continues with only the required pip inventory when
CycloneDX generation is unavailable or invalid.

## T-8 Weeks: Release Branch

1. Choose the target Slicer version.
2. Choose the SlicerOpenLIFU release line for this desktop application release.
3. Create the release branch:

   ```bash
   git checkout main
   git pull
   git checkout -b release/X.Y
   git push -u origin release/X.Y
   ```

4. Update the SlicerOpenLIFU `GIT_TAG` in the top-level `CMakeLists.txt` to the
   current tag from that release line.
5. Confirm the selected SlicerOpenLIFU tag's `openlifu` pin from
   `OpenLIFULib/OpenLIFULib/Resources/python-requirements.txt` in that tag.
6. Bump the numeric desktop application version in
   `Applications/OpenLIFUApp/slicer-application-properties.cmake`.
7. Commit and push the release-branch setup changes.

## T-6 Weeks: First Release Candidate

1. Update the SlicerOpenLIFU `GIT_TAG` to the intended RC or patch tag from the
   selected SlicerOpenLIFU release line, if needed.
2. If the running application should visibly identify this release candidate,
   set `APPLICATION_DISPLAY_NAME` temporarily (discussed above).
3. Add the release-candidate row to
   `docs/release-component-version-table.md`. This script can help generate the
   row for you, but double check the output:

   ```bash
   uv run tools/release_component_version_row.py --app-version vX.Y.Z-rc.1
   ```

4. Commit and push the release-candidate updates.
5. Make sure all tests pass.
6. Build the packages.
7. Rename the packages before uploading them so the filenames include the
   release-candidate tag, such as `vX.Y.Z-rc.1`.
8. Tag the release candidate from the release branch:

   ```bash
   git checkout release/X.Y
   git pull
   git tag vX.Y.Z-rc.1
   git push origin vX.Y.Z-rc.1
   ```

9. Create the GitHub prerelease from `vX.Y.Z-rc.1` and upload the renamed
   packages.

## T-4 Weeks: Additional Release Candidates

If another release candidate is needed, repeat the T-6 week flow with the next
RC tag:

```text
vX.Y.Z-rc.2
vX.Y.Z-rc.3
```

The release branch may take SlicerOpenLIFU RC or patch tags from the selected
SlicerOpenLIFU release line when they contain fixes needed for this desktop
application release. Keep the release component version table updated for each
published release candidate.

## T-2 Weeks: Release Blockers Only

At this point, only release-blocking changes should go into the release branch.
Allowed changes are:

- Desktop application release blockers.
- Package or release-documentation fixes.
- SlicerOpenLIFU RC or patch tags from the selected release line, when they
  contain fixes needed for this desktop application release.

Avoid new feature work, avoid changing dependency lines, and do not advance the
SlicerOpenLIFU pin for unrelated fixes.

## T: Final Release

1. Update the SlicerOpenLIFU `GIT_TAG` to the final intended tag from the
   selected SlicerOpenLIFU release line, if needed.
2. Remove any release-candidate `APPLICATION_DISPLAY_NAME` decoration unless
   the final release intentionally needs a distinct display name.
3. Add the final row to `docs/release-component-version-table.md`:

   ```bash
   uv run tools/release_component_version_row.py --app-version vX.Y.Z
   ```

4. Commit and push the final release updates.
5. Ensure tests pass.
6. Build the final packages. They should end up with correct names if the desktop application version is just `vX.Y.Z`.
7. Sign the macOS and Windows packages.
8. Tag the final release from the release branch:

   ```bash
   git checkout release/X.Y
   git pull
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

9. Create the GitHub release from `vX.Y.Z` and upload the packages.

## Patch Releases

Patch releases come from the existing desktop application release branch:

```text
release/X.Y
  vX.Y.1
```

Use patch releases for important fixes to an already released line, package
fixes, or dependency patch updates needed for the released line.

1. Apply the intended fixes to `release/X.Y`.
2. Update the SlicerOpenLIFU `GIT_TAG` if the patch release takes a newer
   SlicerOpenLIFU patch tag for a fix needed by the released line.
3. Bump the numeric desktop application patch version in
   `Applications/OpenLIFUApp/slicer-application-properties.cmake`.
4. Add the patch row to `docs/release-component-version-table.md`:

   ```bash
   uv run tools/release_component_version_row.py --app-version vX.Y.1
   ```

5. Commit and push the patch updates.
6. Ensure tests pass.
7. Build the packages. They should end up with correct names if the desktop application version is just `vX.Y.Z`.
8. Sign the macOS and Windows packages.
9. Tag the patch release from the release branch:

   ```bash
   git checkout release/X.Y
   git pull
   git tag vX.Y.1
   git push origin vX.Y.1
   ```

10. Create the GitHub release from `vX.Y.1` and upload the renamed packages.
