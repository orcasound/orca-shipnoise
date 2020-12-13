# Contributing to ShipNoise.Net

Welcome to the Orcasound ShipNoise site! We're thrilled you're interested in contributing.

## General Workflow

Here is a sample workflow for contributing:

1. Fork this repo and clone it locally to make local changes
2. Pull the backend by installing the [Amplify CLI](https://docs.amplify.aws/cli). Run `amplify pull` and select the following options:

`? Do you want to use an AWS profile?` **Yes** (Note: You may need to set up an [AWS Profile](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html))
<br/>`? Please choose the profile you want to use` **default**
<br/>`? Which app are you working on?` **d27wklsx9a9q36**
<br/>`? Pick a backend environment:` **dev**
<br/>`? Choose your default editor:` **Visual Studio Code**
<br/>`? Choose the type of app that you're building` **javascript**
<br/>Please tell us about your project
<br/>` What javascript framework are you using` **react**
<br/>`? Source Directory Path:`  **src**
<br/>`? Distribution Directory Path:` **build**
<br/>`? Build Command:`  **npm run-script build**
<br/>`? Start Command:`**npm run-script start**
<br/>`? Do you plan on modifying this backend?` **No** 

Note: For the last option, if you are planning on making any changes to the backend (eg. model changes or API changes), you can select "Yes" instead. You can use `amplify push` to push your backend changes to the `dev` environment.

3. Make your changes locally, run `yarn && yarn start` and open [http://localhost:3000](http://localhost:3000) to 
view your changes in the browser
4. Submit a PR to the `dev` branch of this repo. Once it is merged, a test version of the site will be deployed to https://dev.d27wklsx9a9q36.amplifyapp.com/. If the changes look good, we can merge it into the main branch for deployment to the live ShipNoise.Net site

## Questions?

If you have any questions, you can reach out to [Mahtab Sabet](https://github.com/mahtabsabet).

## Code of Conduct

### Our Pledge

In the interest of fostering an open and welcoming environment, we as
contributors and maintainers pledge to making participation in our project and
our community a harassment-free experience for everyone, regardless of age, body
size, disability, ethnicity, gender identity and expression, level of experience,
nationality, personal appearance, race, religion, or sexual identity and
orientation.

### Our Standards

Examples of behavior that contributes to creating a positive environment
include:

* Using welcoming and inclusive language
* Being respectful of differing viewpoints and experiences
* Gracefully accepting constructive criticism
* Focusing on what is best for the community
* Showing empathy towards other community members

Examples of unacceptable behavior by participants include:

* The use of sexualized language or imagery and unwelcome sexual attention or
advances
* Trolling, insulting/derogatory comments, and personal or political attacks
* Public or private harassment
* Publishing others' private information, such as a physical or electronic
  address, without explicit permission
* Other conduct which could reasonably be considered inappropriate in a
  professional setting

### Our Responsibilities

Project maintainers are responsible for clarifying the standards of acceptable
behavior and are expected to take appropriate and fair corrective action in
response to any instances of unacceptable behavior.

Project maintainers have the right and responsibility to remove, edit, or
reject comments, commits, code, wiki edits, issues, and other contributions
that are not aligned to this Code of Conduct, or to ban temporarily or
permanently any contributor for other behaviors that they deem inappropriate,
threatening, offensive, or harmful.

### Scope

This Code of Conduct applies both within project spaces and in public spaces
when an individual is representing the project or its community. Examples of
representing a project or community include using an official project e-mail
address, posting via an official social media account, or acting as an appointed
representative at an online or offline event. Representation of a project may be
further defined and clarified by project maintainers.

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be
reported by contacting the project team at admin@orcasound.net. All
complaints will be reviewed and investigated and will result in a response that
is deemed necessary and appropriate to the circumstances. The project team is
obligated to maintain confidentiality with regard to the reporter of an incident.
Further details of specific enforcement policies may be posted separately.

Project maintainers who do not follow or enforce the Code of Conduct in good
faith may face temporary or permanent repercussions as determined by other
members of the project's leadership.

### Attribution

This Code of Conduct is adapted from the [Contributor Covenant][homepage], version 1.4,
available at [http://contributor-covenant.org/version/1/4][version]

[homepage]: http://contributor-covenant.org
[version]: http://contributor-covenant.org/version/1/4/