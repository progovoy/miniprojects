#!/usr/bin/python
import urllib2
import json
import string
import sys
from distutils.version import LooseVersion


class DockerPuller(object):
    def __init__(self):
        pass

    def _get_credentials(self, repo_name, auth=None):
        request = urllib2.Request(
            '{0}/v1/repositories/{1}/images'.format(self.BASE_INDEX_REGISTRY_URL, repo_name))
        request.add_header('User-Agent', self.USER_AGENT)
        request.add_header('X-Docker-Token', 'true')

        if auth:
            base64_res = '{0}:{1}'.format(auth['username'], auth['password']).encode('base64')
            request.add_header('Authorization', 'basic {0}'.format(base64_res))
        try:
            response = urllib2.urlopen(request)
        except Exception:
            print 'Caught exception for link:'
            print '{0}/v1/repositories/{1}/images'.format(self.BASE_INDEX_REGISTRY_URL, repo_name)
            raise ValueError('{0} is dead link'.format(repo_name), repo_name)

        ret_dict = {}
        ret_dict['token'] = response.info().getheader('X-Docker-Token')
        # TODO::We assume only one endpoint. May be several (maybe take only the first)
        ret_dict['endpoint'] = response.info().getheader('X-Docker-Endpoints')
        ret_dict['endpoint'] = 'https://{0}'.format(ret_dict['endpoint'])

        return ret_dict

    def _get_tags(self, repo_name, creds):
        request = urllib2.Request(
            '{0}/v1/repositories/{1}/tags'.format(creds['endpoint'], repo_name))
        request.add_header('User-Agent', self.USER_AGENT)
        request.add_header('Authorization', 'Token {0}'.format(creds['token']))
        try:
            response = urllib2.urlopen(request)
        except Exception:
            print 'Caught exception for link:'
            print '{0}/v1/repositories/{1}/tags'.format(creds['endpoint'], repo_name)
            raise Exception('TODO:: add exception')

        tags = {}
        data = json.load(response)
        for ver, ver_hash in data.iteritems():
            if ver == 'latest':
                #continue
                tags[ver_hash] = ver
            if ver_hash in tags:
                #if LooseVersion(tags[ver_hash]) < LooseVersion(ver):
                #    tags[ver_hash] = ver
                continue
            else:
                #tags[ver_hash] = ver
                continue

        inv_tags = {v: k for k, v in tags.items()}

        return inv_tags

    def _get_layers(self, tag_hash, creds):
        request = urllib2.Request(
            '{0}/v1/images/{1}/ancestry'.format(creds['endpoint'], tag_hash))
        request.add_header('User-Agent', self.USER_AGENT)
        request.add_header('Authorization', 'Token {0}'.format(creds['token']))
        try:
            response = urllib2.urlopen(request)
        except Exception:
            print 'Caught exception for link:'
            print '{0}/v1/images/{1}/ancestry'.format(creds['endpoint'], tag_hash)
            raise Exception('TODO:: add exception')

        layers = json.load(response)

        return layers

    def _get_layer_info(self, layer, creds):
        request = urllib2.Request(
            '{0}/v1/images/{1}/json'.format(creds['endpoint'], layer))
        request.add_header('User-Agent', self.USER_AGENT)
        request.add_header('Authorization', 'Token {0}'.format(creds['token']))
        try:
            response = urllib2.urlopen(request)
        except Exception:
            print 'Caught exception for link:'
            print '{0}/v1/images/{1}/json'.format(creds['endpoint'], layer)
            raise Exception('TODO:: add exception')

        layer_info = json.load(response)

        return layer_info

    def _download_layer_tar(self, layer, creds, target_path=None):
        file_name = '{0}.tar'.format(layer)
        if target_path:
            file_name = '{0}/{1}'.format(target_path, file_name)

        request = urllib2.Request(
            '{0}/v1/images/{1}/layer'.format(creds['endpoint'], layer))
        request.add_header('User-Agent', self.USER_AGENT)
        request.add_header('Authorization', 'Token {0}'.format(creds['token']))
        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError, error:
            msg = error.read()
            if 'not found' in msg:
                raise ValueError("layer not found")
            else:
                raise KeyError("something else")

        print 'Downloading to: {0}'.format(file_name)
        with open(file_name, 'wb') as f:
            meta = response.info()
            file_size = int(meta.getheaders("Content-Length")[0])
            print 'Downloading: {0} with size of: {1} Bytes'.format(file_name, file_size)

            file_size_dl = 0
            block_sz = 8192
            while True:
                buffer = response.read(block_sz)
                if not buffer:
                    break

                file_size_dl += len(buffer)
                f.write(buffer)
                status = r'%10d  [%3.2f%%]' % (file_size_dl, file_size_dl * 100. / file_size)
                status = status + chr(8)*(len(status) + 1)
                # print status,

    def pull_repo(self, repo_name, auth=None):
        try:
            creds = self._get_credentials(repo_name, auth)
        except Exception:
            print 'get credentials'
            # raise Exception('TODO:: add some exception')

        tags = self._get_tags(repo_name, creds)

        for tag_ver, tag_hash in tags.iteritems():
            layers = self._get_layers(tag_hash, creds)
            for layer in layers:
                try:
                    layer_info = self._get_layer_info(layer, creds)
                except Exception:
                    continue

                print layer_info['Size']

                if (int(layer_info['Size']) < 30000000):
                    continue

                self._download_layer_tar(layer, creds)

    def download_layer(self, repo_name, layer_name, target_path, auth=None):
        try:
            creds = self._get_credentials(repo_name, auth)
        except ValueError as e:
            raise ValueError(e[0], e[1])
        self._download_layer_tar(layer_name, creds, target_path)

    USER_AGENT = 'docker/1.6.2 go/go1.2.1 git-commit/7c8fca2 kernel/3.19.0-42-generic os/linux arch/amd64'
    BASE_INDEX_REGISTRY_URL = 'https://index.docker.io'


class DockerImageHandler(object):

    def __init__(self):
        pass

    def initialize(self):
        pass


class DockerReposInfoCollector(object):

    """This is a Docker repos names grabber class"""

    def __init__(self):
        pass

    def initialize(self):
        pass

    def extract_repos_info(self):
        for extrator in self._extrators:
            extrator(self)

        for cur_info_key, cur_info_val in self._images_dict.iteritems():
            print 'Currently gathering info for repo: {0}'.format(cur_info_key)
            try:
                creds = self._puller._get_credentials(cur_info_key)
            except Exception:
                continue
            try:
                tags = self._puller._get_tags(cur_info_key, creds)
            except Exception:
                continue

            repo_info = {'tags': {}}
            for tag_ver, tag_hash in tags.iteritems():
                repo_info['tags'][tag_ver] = {}
                repo_info['tags'][tag_ver]['hash'] = tag_hash
                repo_info['tags'][tag_ver]['layers'] = {}

                try:
                    layers = self._puller._get_layers(tag_hash, creds)
                except Exception:
                    continue

                for layer in layers:
                    try:
                        layer_info = self._puller._get_layer_info(layer, creds)
                    except Exception:
                        continue

                    repo_info['tags'][tag_ver]['layers'][layer] = layer_info

            cur_info_val.update(repo_info)

        with open('res.json', 'w+') as f:
            json.dump(self._images_dict, f, indent=4)

    def _extract_from_google(self):
        pass

    def _extract_officials(self):
        try:
            response = urllib2.urlopen('{0}{1}'.format(self.BASE_REGISTRY_URL, 'library'))
        except Exception as exc:
            print 'Caught exception for link:'
            print '{0}{1}'.format(self.BASE_REGISTRY_URL, 'library')
            print exc
            # raise Exception('TODO:: add some exception')

        self.__handle_search_response(response, 'library')

    def _extract_kolla(self):
        try:
            response = urllib2.urlopen('{0}{1}'.format(self.BASE_REGISTRY_URL, 'kolla'))
        except Exception:
            print 'Caught exception for link:'
            print '{0}{1}'.format(self.BASE_REGISTRY_URL, 'kolla')
            # raise Exception('TODO:: add some exception')

        self.__handle_search_response(response, 'kolla')

    def _extract_printable(self):
        for chr in list(string.printable):
            try:
                response = urllib2.urlopen('{0}{1}'.format(self.BASE_REGISTRY_URL, chr))
            except Exception:
                print 'Continue to next char. Caught exception for link:'
                print '{0}{1}'.format(self.BASE_REGISTRY_URL, chr)
                continue

            self.__handle_search_response(response, chr)

    def __handle_search_response(self, response, search_pattern):
        data = json.load(response)
        num_pages = data['num_pages']
        print 'Currently searching: {0} with {1} pages'.format(search_pattern, num_pages)
        for page_num in xrange(0, int(num_pages)):
            try:
                response = urllib2.urlopen('{0}{1}&page={2}'.format(self.BASE_REGISTRY_URL, search_pattern, str(page_num)))
            except Exception:
                print 'Continue to next char. Caught exception for link:'
                print '{0}{1}&page={2}'.format(self.BASE_REGISTRY_URL, search_pattern, str(page_num))
                break

            data = json.load(response)
            self.__handle_search_result_page(data)

    def __handle_search_result_page(self, page_result):
        for result in page_result['results']:
            if result['name'] not in self._images_dict:
                self._images_dict[result['name']] = {k: result[k] for k in result.keys() if k != 'name'}

    _puller = DockerPuller()
    _images_dict = {}

    # _extrators = (_extract_officials, _extract_printable, _extract_from_google)
    _extrators = (_extract_kolla, )
    BASE_REGISTRY_URL = 'https://index.docker.io/v1/search?q='


def main():
    grabber = DockerReposInfoCollector()
    grabber.extract_repos_info()
    # puller = DockerPuller()
    # puller.pull_repo('library/mysql')

if __name__ == '__main__':
    main()
