from pathlib import Path
import os
import jinja2 as j2

TEMPLATE_FILE = 'bitbucket-pipelines.yml.j2'
images = {

    'Bamboo': {
        17: {
            'mac_key': 'bamboo',
            'start_version': '9.4',
            'default_release': True,
            'base_image': 'eclipse-temurin:17',
            'tag_suffixes': ['jdk17', 'ubuntu'],
            'dockerfile': 'Dockerfile',
            'docker_repos': ['atlassian/bamboo', 'atlassian/bamboo-server'],
        },
        11: {
            'mac_key': 'bamboo',
            'start_version': '8',
            'default_release': True,
            'base_image': 'eclipse-temurin:11',
            'tag_suffixes': ['jdk11', 'ubuntu'],
            'dockerfile': 'Dockerfile',
            'docker_repos': ['atlassian/bamboo', 'atlassian/bamboo-server'],
        },
        8: {
            'mac_key': 'bamboo',
            'start_version': '7.1',
            'end_version': '8',
            'default_release': True,
            'base_image': 'eclipse-temurin:8',
            'tag_suffixes': ['jdk8', 'ubuntu'],
            'dockerfile': 'Dockerfile',
            'docker_repos': ['atlassian/bamboo', 'atlassian/bamboo-server'],
        }
    }
}


def main():
    jenv = j2.Environment(
        loader=j2.FileSystemLoader('.'),
        lstrip_blocks=True,
        trim_blocks=True)
    template = jenv.get_template(TEMPLATE_FILE)
    generated_output = template.render(images=images, batches=8)

    print(generated_output)

if __name__ == '__main__':
    main()
