import pytest


@pytest.mark.asyncio
async def test_get_profile_auto_creates(auth_client):
    response = await auth_client.get("/api/profile")
    assert response.status_code == 200
    body = response.json()
    assert body["first_name"] == "Fix"
    assert body["education"] == []


@pytest.mark.asyncio
async def test_profile_requires_auth(client):
    response = await client.get("/api/profile")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_profile_personal_info_and_preferences(auth_client):
    response = await auth_client.put(
        "/api/profile",
        json={
            "first_name": "Ankita",
            "last_name": "Makkar",
            "city": "Bengaluru",
            "country": "India",
            "job_types": ["internship", "full_time"],
            "work_modes": ["remote", "hybrid"],
            "preferred_locations": ["India", "Remote"],
            "min_salary": 10000,
            "experience_level": "fresher",
            "preferred_roles": ["Software Engineer"],
            "preferred_skills": ["Python", "SQL"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["city"] == "Bengaluru"
    assert body["job_types"] == ["internship", "full_time"]
    assert body["min_salary"] == 10000


@pytest.mark.asyncio
async def test_education_crud(auth_client):
    create = await auth_client.post(
        "/api/profile/education",
        json={
            "degree": "B.Tech",
            "university": "IIT Guwahati",
            "major": "CSE",
            "graduation_year": 2027,
            "cgpa": 8.9,
            "relevant_coursework": ["DSA", "OS"],
        },
    )
    assert create.status_code == 201
    edu_id = create.json()["id"]

    listing = await auth_client.get("/api/profile/education")
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    update = await auth_client.put(
        f"/api/profile/education/{edu_id}",
        json={"degree": "B.Tech", "university": "IIT Guwahati", "major": "CSE", "graduation_year": 2028},
    )
    assert update.status_code == 200
    assert update.json()["graduation_year"] == 2028

    delete = await auth_client.delete(f"/api/profile/education/{edu_id}")
    assert delete.status_code == 204

    listing_after = await auth_client.get("/api/profile/education")
    assert listing_after.json() == []


@pytest.mark.asyncio
async def test_skills_crud(auth_client):
    create = await auth_client.post("/api/profile/skills", json={"name": "Python", "category": "programming_languages"})
    assert create.status_code == 201

    listing = await auth_client.get("/api/profile/skills")
    assert len(listing.json()) == 1
    assert listing.json()[0]["name"] == "Python"


@pytest.mark.asyncio
async def test_child_resource_scoped_to_owner(client):
    # user A creates an experience entry
    reg_a = await client.post(
        "/api/auth/register", json={"email": "a@example.com", "password": "supersecret1"}
    )
    token_a = reg_a.json()["access_token"]
    create = await client.post(
        "/api/profile/experience",
        json={"company": "Acme", "position": "SWE", "start_date": "2024-01"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    exp_id = create.json()["id"]

    # user B must not be able to see or modify it
    reg_b = await client.post(
        "/api/auth/register", json={"email": "b@example.com", "password": "supersecret1"}
    )
    token_b = reg_b.json()["access_token"]
    listing_b = await client.get(
        "/api/profile/experience", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert listing_b.json() == []

    update_b = await client.put(
        f"/api/profile/experience/{exp_id}",
        json={"company": "Hacked"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert update_b.status_code == 404
