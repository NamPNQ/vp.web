import json
import math

from django.core.exceptions import PermissionDenied

from django.shortcuts import render, render_to_response
from django.template import RequestContext
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.http.response import HttpResponseRedirect
from django.contrib.auth.decorators import login_required

from vpw.models import Material
from vpw.vpr_api import vpr_get_material, vpr_get_category, vpr_get_person, \
    vpr_get_categories, vpr_browse, vpr_materials_by_author, vpr_get_pdf, vpr_search, vpr_delete_person


# Create your views here.

def home(request):
    material_features = ['64b4a7a7', 'fd2f579c', 'f2feed3c', '4dbdd6c5', 'c3ad3533', '0e60bfc6']
    materials_list = []
    for mid in material_features:
        material = vpr_get_material(mid)
        author_id_list = material['author'].split(',')

        p_list = []
        for pid in author_id_list:
            pid = pid.strip()
            person = vpr_get_person(pid)
            if person['fullname']:
                p_list.append({'pid': pid, 'pname': person['fullname']})
            else:
                p_list.append({'pid': pid, 'pname': person['fullname']})
        material['author_list'] = p_list
        materials_list.append(material)

    # Get featured authors
    person_features = [50, 76, 34, 54, 23]
    person_list = []
    for pid in person_features:
        person = vpr_get_person(pid)
        person_list.append(person)

    return render(request, "frontend/index.html", {"materials_list": materials_list, "person_list": person_list})


def signup(request):
    return render(request, "frontend/signup.html")


def aboutus(request):
    return render(request, "frontend/aboutus.html")


def module_detail(request, mid, version):
    material = vpr_get_material(mid)
    author = vpr_get_person(material['author'])
    category = vpr_get_category(material['categories'])
    return render(request, "frontend/module_detail.html",
                  {"material": material, "author": author, "category": category})


def collection_detail(request, cid, mid):
    # Get collection
    collection = vpr_get_material(cid)
    outline = json.loads(collection['text'])

    if not mid:
        # get the first material of collection
        mid = get_first_material_id(outline['content'])

    # Get material in collection
    material = vpr_get_material(mid)
    # Generate outline html
    strOutline = "<ul class='list-module-name-content'>%s</ul>" % get_outline(cid, outline['content'])

    author = vpr_get_person(collection['author'])
    category = vpr_get_category(collection['categories'])

    return render(request, "frontend/collection_detail.html",
                  {"collection": collection, "material": material, "author": author, "category": category,
                   "outline": strOutline})


@login_required
def create_module(request):
    if request.method == "POST":
        try:
            current_step = int(request.POST.get("step", "0"))
        except ValueError:
            current_step = 0

        categories = vpr_get_categories()
        if current_step == 1:
            return render(request, "frontend/module/create_step2.html", {"categories": categories})

        if current_step == 2:
            # Save metadata
            title = request.POST.get("title", "")
            description = request.POST.get("description", "")
            keywords = request.POST.get("keywords", "")
            tags = request.POST.get("tags", "")
            language = request.POST.get("language", "")
            categories = request.POST.get('categories', "")
            material = Material()
            material.title = title
            material.description = description
            material.keywords = keywords
            material.categories = categories
            material.language = language
            # material.save()
            material = Material.objects.get(id=1)
            if material.id:
                return render(request, "frontend/module/create_step3.html",
                              {"material": material, "categories": categories})

        if current_step == 3:
            #Save content & metadata, or publish to VPR
            pass
    else:
        return render(request, "frontend/module/create_step1.html")


@login_required
def create_collection(request):
    step = request.GET.get('step', '')
    print "Step: " + step
    if step == 1:
        return render(request, "frontend/collection/create_step1.html")
    elif step == 2:
        return render(request, "frontend/collection/create_step2.html")
    elif step == 3:
        return render(request, "frontend/collection/create_step3.html")
    else:
        return render(request, "frontend/collection/create_step1.html")
    return render(request, "frontend/collection/create_step1.html")


def view_profile(request, pid):
    current_person = vpr_get_person(pid, True)
    materials = vpr_materials_by_author(pid)
    materials = materials['results']

    person_materials = []
    for material in materials:
        author_id_list = material['author'].split(',')

        p_list = []
        for pid in author_id_list:
            pid = pid.strip()
            person = vpr_get_person(pid)
            if person['fullname']:
                p_list.append({'pid': pid, 'pname': person['fullname']})
            else:
                p_list.append({'pid': pid, 'pname': person['fullname']})
        material['author_list'] = p_list
        person_materials.append(material)

    return render_to_response("frontend/profile.html", {"person": current_person, "materials": person_materials},
                              context_instance=RequestContext(request))

def delete_profile(request, pid):
    if not request.user.is_superuser:
        raise PermissionDenied
    result = vpr_delete_person(pid)
    if result == "204":
        print "Xoa thanh cong!"
    return HttpResponseRedirect('/')

'''
Browse page
'''


def browse(request):
    page = int(request.GET.get('page', 1))
    categories = vpr_get_categories()

    cats = request.GET.get("categories", "")
    types = request.GET.get("types", "")
    languages = request.GET.get("languages", "")

    materials = vpr_browse(page=page, categories=cats, types=types, languages=languages)
    pager = pager_default_initialize(materials['count'], 12, page)
    page_query = get_page_query(request)

    return render(request, "frontend/browse.html", {"materials": materials, "categories": categories, 'pager': pager, 'page_query': page_query})


def vpw_authenticate(request):
    username = request.POST['username']
    password = request.POST['password']
    print username + "|" + password
    user = authenticate(username=username, password=password)

    response_data = {}
    response_data['status'] = False
    response_data['message'] = 'The username or password is incorrect.'

    if user is not None:
        if user.is_active:
            login(request, user)
            response_data['status'] = True

    if request.is_ajax():
        return HttpResponse(json.dumps(response_data), content_type="application/json")
    else:
        return HttpResponseRedirect('/')


def vpw_logout(request):
    logout(request)
    return HttpResponseRedirect('/')


@login_required
def user_profile(request):
    current_user = request.user
    pid = current_user.author.author_id
    author = vpr_get_person(pid, True)
    materials = vpr_materials_by_author(pid)
    return render(request, "frontend/user_profile.html", {"materials": materials, "author": author})


def search_result(request):
    keyword = request.REQUEST.get('keyword', '')
    page = int(request.GET.get('page', 1))

    page_query = get_page_query(request)

    search_results = vpr_search(keyword, page)
    pager = pager_default_initialize(search_results['count'], 12, page)
    search_results = search_results['results']

    categories = vpr_get_categories()
    category_dict = {}
    for category in categories:
        category_dict[category['id']] = category['name']

    result_array = []
    for result in search_results:
        if result['user_id']:
            if (result.has_key('fullname') and result['fullname']):
                result['title'] = result['fullname']
            else:
                result['title'] = result['user_id']

            if (result.has_key('affiliation') and result['affiliation']):
                result['description'] = result['affiliation']

        if result.has_key('author'):
            author_array = result['author'].split(',')
            person_list = []
            for pid in author_array:
                pid = pid.strip()
                person = vpr_get_person(pid)
                if person['fullname']:
                    person_list.append({'pid': pid, 'pname': person['fullname']})
                else:
                    person_list.append({'pid': pid, 'pname': person['fullname']})
            result['person_list'] = person_list

        if (result.has_key('categories') and result['categories']):
            category_array = result['categories'].split(',')
            category_list = []
            for cid in category_array:
                cid = cid.strip()
                category_list.append({'cid': cid, 'cname': category_dict.get(int(cid))})

            result['category_list'] = category_list

        result_array.append(result)

    return render(request, "frontend/search_result.html", {'keyword': keyword, "search_results": result_array, 'pager': pager, 'page_query': page_query})


def get_pdf(request, mid, version):
    # mid = request.GET.get("mid", "")
    # version = request.GET.get("version", "")

    pdf_content = vpr_get_pdf(mid, version)
    print pdf_content
    return HttpResponse(pdf_content, mimetype='application/pdf')


###### UTILITIES FUNCTION #######
def get_first_material_id(outline):
    for item in outline:
        # import pdb;pdb.set_trace()
        if item.has_key('content'):
            return get_first_material_id(item['content'])
        else:
            return item['id']

    return ''


def get_outline(cid, outline):
    result = ""
    for item in outline:
        print item
        if item['type'] == "module":
            result += "<li><a href='/c/%s/%s'>%s</a></li>" % (cid, item['id'], item['title'])
        else:
            strli = "<li>"
            strli += "<a>%s</a>" % item['title']
            strli += "<ul>"
            strli += get_outline(cid, item['content'])
            strli += "</ul>"
            strli += "</li>"
            result += strli

    return result

def pager_default_initialize(count, limit, current_page=1, page_rank=4):
    pager_array = []
    page_total = int(math.ceil((count + limit - 1) / limit))

    if current_page > 1:
        page_temp = {}
        page_temp['text'] = '<<'
        page_temp['value'] = 1
        pager_array.append(page_temp)

        page_temp = {}
        page_temp['text'] = '<'
        page_temp['value'] = current_page - 1
        pager_array.append(page_temp)

    if current_page > page_rank:
        if (current_page - page_rank >= 2):
            page_temp = {}
            page_temp['text'] = '...'
            page_temp['value'] = ''
            pager_array.append(page_temp)

        for i in range(0, page_rank):
            xpage = current_page - page_rank + i

            page_temp = {}
            page_temp['text'] = xpage
            page_temp['value'] = xpage
            pager_array.append(page_temp)
    else :
        for i in range(1, current_page):
            page_temp = {}
            page_temp['text'] = i
            page_temp['value'] = i
            pager_array.append(page_temp)

    page_temp = {}
    page_temp['text'] = current_page
    page_temp['value'] = ''
    pager_array.append(page_temp)

    if (current_page + page_rank < page_total):
        for i in range(1, page_rank + 1):
            xpage = current_page + i
            page_temp = {}
            page_temp['text'] = xpage
            page_temp['value'] = xpage
            pager_array.append(page_temp)

        if (current_page + page_rank + 2 <= page_total):
            page_temp = {}
            page_temp['text'] = '...'
            page_temp['value'] = ''
            pager_array.append(page_temp)
    else :
        for i in range(current_page+1, page_total+1):
            page_temp = {}
            page_temp['text'] = i
            page_temp['value'] = i
            pager_array.append(page_temp)

    if current_page < page_total:
        page_temp = {}
        page_temp['text'] = '>'
        page_temp['value'] = current_page + 1
        pager_array.append(page_temp)

        page_temp = {}
        page_temp['text'] = '>>'
        page_temp['value'] = page_total
        pager_array.append(page_temp)

    if len(pager_array) > 1 :
        return pager_array

    return []

def get_page_query(request):
    page = request.GET.get('page', 1)
    page_query = request.path.encode("utf8") + "?" + request.META.get('QUERY_STRING').encode("utf8")
    page_query = page_query.replace('&page=' + str(page), '')

    return page_query

## Browse material
def ajax_browse(request):
    page = int(request.GET.get('page', 1))
    categories = vpr_get_categories()

    cats = request.GET.get("categories", "")
    types = request.GET.get("types", "")
    languages = request.GET.get("languages", "")

    materials = vpr_browse(page=page, categories=cats, types=types, languages=languages)
    pager = pager_default_initialize(materials['count'], 12, page)
    page_query = get_page_query(request)

    return render(request, "frontend/ajax/browse.html", {"materials": materials, "categories": categories, 'pager': pager, 'page_query': page_query})
