# David_igou Linux_baseline Collection

This repository contains the `david_igou.linux_baseline` Ansible Collection.

<!--start requires_ansible-->
<!--end requires_ansible-->

## External requirements

Some modules and plugins require external libraries. Please check the
requirements for each plugin or module you use in the documentation to find out
which requirements are needed.

## Included content

<!--start collection content-->
<!--end collection content-->

## Using this collection

```bash
    ansible-galaxy collection install david_igou.linux_baseline
```

You can also include it in a `requirements.yml` file and install it via
`ansible-galaxy collection install -r requirements.yml` using the format:

```yaml
collections:
  - name: david_igou.linux_baseline
```

To upgrade the collection to the latest available version, run the following
command:

```bash
ansible-galaxy collection install david_igou.linux_baseline --upgrade
```

You can also install a specific version of the collection, for example, if you
need to downgrade when something is broken in the latest version (please report
an issue in this repository). Use the following syntax where `X.Y.Z` can be any
[available version](https://galaxy.ansible.com/david_igou/linux_baseline):

```bash
ansible-galaxy collection install david_igou.linux_baseline:==X.Y.Z
```

See
[Ansible Using Collections](https://docs.ansible.com/ansible/latest/user_guide/collections_using.html)
for more details.

## Testing with Molecule

Each role has a scenario under `extensions/molecule/<role>/` driven by
`david_igou.molecule_provisioners`. Pick a backend with the `PROVISIONER`
env var; the same scenarios run on all four:

```bash
MOLECULE_GLOB='extensions/molecule/*/molecule.yml' \
PROVISIONER=podman molecule test --scenario-name sshd

# Other backends:
PROVISIONER=docker   molecule test --scenario-name sshd
PROVISIONER=kubevirt molecule test --scenario-name sshd
PROVISIONER=qemu     molecule test --scenario-name sshd
```

`MOLECULE_GLOB` tells molecule to discover scenarios under `extensions/`
(collection layout). Scenarios: `auto_updates`, `chrony`, `common`,
`firewalld`, `journald`, `sshd`, `sudoers`.

The provisioner collection is installed by molecule's `dependency` step
from each scenario's `collections.yml` — you don't need to add it to
`requirements.yml` for downstream consumers of the roles.

### Backend prerequisites

| Backend  | Controller needs                                                                       |
| -------- | -------------------------------------------------------------------------------------- |
| podman   | `podman`                                                                               |
| docker   | running docker daemon + `docker` python package                                        |
| kubevirt | `kubectl`/`oc` + kubeconfig with `nodes [get,list]` cluster-scope and namespaced perms for VMs/Services |
| qemu     | `qemu-system-x86_64`, `qemu-img`, `cloud-localds`                                      |

### Backend caveats

| Role         | container backends (podman/docker)             | VM backends (kubevirt/qemu) |
| ------------ | ---------------------------------------------- | --------------------------- |
| firewalld    | netfilter unavailable → daemon not started; verify checks XML on disk | full daemon running |
| common (auditd) | CAP_AUDIT_CONTROL not granted → not started | full daemon running |
| chrony       | CAP_SYS_TIME not granted → daemon flaps      | full daemon running |
| auto_updates | dnf-automatic.timer enabled but not active   | timer enabled + scheduled   |
| sshd, sudoers, journald | full verification | full verification |

`verify.yml` gates runtime/daemon assertions on `mp_systemd_runtime` +
`not mp_is_container`; file artifacts and idempotency are checked on
every backend.

## Release notes

See the
[changelog](https://github.com/ansible-collections/david_igou.linux_baseline/tree/main/CHANGELOG.rst).

## Roadmap

<!-- Optional. Include the roadmap for this collection, and the proposed release/versioning strategy so users can anticipate the upgrade/update cycle. -->

## More information

<!-- List out where the user can find additional information, such as working group meeting times, slack/matrix channels, or documentation for the product this collection automates. At a minimum, link to: -->

- [Ansible collection development forum](https://forum.ansible.com/c/project/collection-development/27)
- [Ansible User guide](https://docs.ansible.com/ansible/devel/user_guide/index.html)
- [Ansible Developer guide](https://docs.ansible.com/ansible/devel/dev_guide/index.html)
- [Ansible Collections Checklist](https://docs.ansible.com/ansible/devel/community/collection_contributors/collection_requirements.html)
- [Ansible Community code of conduct](https://docs.ansible.com/ansible/devel/community/code_of_conduct.html)
- [The Bullhorn (the Ansible Contributor newsletter)](https://docs.ansible.com/ansible/devel/community/communication.html#the-bullhorn)
- [News for Maintainers](https://forum.ansible.com/tag/news-for-maintainers)

## Licensing

GNU General Public License v3.0 or later.

See [LICENSE](https://www.gnu.org/licenses/gpl-3.0.txt) to see the full text.
