# vbm-dev

## Quellen:

Projektordner mit dem Kunden: https://projects.univention.de/owncloud/f/14912

Guter Gesamtüberblick geht aus dem CR Dokument hervor: https://projects.univention.de/owncloud/f/14912

## Kundenkonto:

Service-Center BILDUNGSLOGIN bei der VBM Service GmbH (172906)

## Build pipline:

The packages are build using a gitlab pipeline. The pipeline is executed for any package which had changes to `debian/changelog`

## Packages:

The packages are build for release `4.4` with scope `vbm`. The repository can be added by adding the following to `/etc/apt/sources.list`
```
deb [trusted=yes] http://192.168.0.10/build2/ ucs_4.4-0-vbm/all/
deb [trusted=yes] http://192.168.0.10/build2/ ucs_4.4-0-vbm/$(ARCH)/
```

## Jenkins:

A [Jenkins Job](https://jenkins.knut.univention.de:8181/job/Customers/job/172906_vbm/job/VBM%20-%20Development%20QA%20Test/) will deploy a school environment with scope `vbm` and run the tests. The [configuration files](https://git.knut.univention.de/univention/prof-services/jenkins-cfgs/-/tree/master/vbm-project) are in a separate repository.
