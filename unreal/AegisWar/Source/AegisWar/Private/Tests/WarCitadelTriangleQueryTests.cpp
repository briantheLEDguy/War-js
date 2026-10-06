#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Chaos/TriangleMeshImplicitObject.h"
#include "Chaos/GeometryQueries.h"
#include "WarCitadelCookedContacts.h"

namespace
{
    TUniquePtr<Chaos::FTriangleMeshImplicitObject> TriangleMesh(const TArray<FVector>& Vertices)
    {
        Chaos::FTriangleMeshImplicitObject::ParticlesType Particles;Particles.AddParticles(Vertices.Num());
        for (int32 I=0;I<Vertices.Num();++I) Particles.SetX(I,Chaos::FVec3f(Vertices[I]));
        TArray<Chaos::TVec3<int32>> Faces;
        for (int32 I=0;I<Vertices.Num();I+=3) Faces.Add(Chaos::TVec3<int32>(I,I+1,I+2));
        return MakeUnique<Chaos::FTriangleMeshImplicitObject>(MoveTemp(Particles),MoveTemp(Faces),TArray<uint16>());
    }
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCitadelTriangleQueryTest,"AegisWar.Foundation.CitadelTriangleQueryDiagnostic",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarCitadelTriangleQueryTest::RunTest(const FString& Parameters)
{
    // Exact live cooked faces from our authored stair mesh, not a licensed mesh.
    // Historical diagnostic: proofs/1791230301072-10356, X12160/Y-5658.
    // This reproduces query disagreement; it grants no route admission.
    const FVector Center(12160,-5658,4254.425860524177);
    const Chaos::FCapsule Capsule(Chaos::FVec3(0,0,-54),Chaos::FVec3(0,0,54),42);
    const Chaos::FRigidTransform3 Pose(Center,Chaos::FRotation3::Identity);
    const int32 CookedIds[]={114,115,116,118,4783,4785,4800,4801};
    const TArray<FVector> Vertices={
        {12200,-5700,4173.7001953125},{12200,-6236.36376953125,4173.7001953125},{12300,-5700,4205.5},
        {12300,-5700,4205.5},{12200,-6236.36376953125,4173.7001953125},{12300,-6218.181640625,4205.5},
        {12200,-5700,4173.7001953125},{12100,-6254.54541015625,4110.0498046875},{12200,-6236.36376953125,4173.7001953125},
        {12100,-5700,4110.0498046875},{12100,-6254.54541015625,4110.0498046875},{12200,-5700,4173.7001953125},
        {12200,-4500,4173.7001953125},{12100,-5700,4110.0498046875},{12200,-5700,4173.7001953125},
        {12100,-4500,4110.0498046875},{12100,-5700,4110.0498046875},{12200,-4500,4173.7001953125},
        {12200,-5700,4173.7001953125},{12300,-5081.818359375,4205.5},{12200,-5100,4173.7001953125},
        {12300,-5700,4205.5},{12300,-5081.818359375,4205.5},{12200,-5700,4173.7001953125}
    };
    int32 Disagreements=0;
    for (int32 I=0;I<UE_ARRAY_COUNT(CookedIds);++I)
    {
        auto Mesh=TriangleMesh({Vertices[I*3],Vertices[I*3+1],Vertices[I*3+2]});
        Chaos::FMTDInfo Mtd{};
        const bool Without=Mesh->OverlapGeom(Capsule,Pose,0,nullptr),With=Mesh->OverlapGeom(Capsule,Pose,0,&Mtd);
        AddInfo(FString::Printf(TEXT("Authored cooked face %d: no-MTD=%d MTD=%d"),CookedIds[I],Without,With));
        TestFalse(TEXT("Separated authored face has no native GJK penetration"),With);
        const auto Certificate=WarCitadelCookedContacts::TriangleSeparation(Center-FVector(0,0,54),Center+FVector(0,0,54),42,
            Vertices[I*3],Vertices[I*3+1],Vertices[I*3+2]);
        TestTrue(TEXT("A separating plane certifies the whole exact authored face and full capsule"),Certificate.Certified);
        TestTrue(TEXT("Separation exceeds the explicit numerical uncertainty guard"),Certificate.SeparatingPlaneGapCm>Certificate.NumericalGuardCm);
        TestTrue(TEXT("The winning plane is recorded for independent projection audit"),Certificate.ProjectionAxisRecorded);
        TestTrue(TEXT("The exported axis retains unit length"),FMath::Abs(Certificate.SeparatingAxis.SizeSquared()-1)<1.e-10);
        for (int32 Vertex=0;Vertex<3;++Vertex)
        {
            const double Projection=FVector::DotProduct(Vertices[I*3+Vertex]-Certificate.ProjectionOrigin,Certificate.SeparatingAxis);
            TestTrue(TEXT("Every cooked vertex lies inside the recorded whole-triangle interval"),
                Projection>=Certificate.TriangleMinimum-1.e-8 && Projection<=Certificate.TriangleMaximum+1.e-8);
        }
        TestTrue(TEXT("Full-radius capsule interval includes the entire axis and both spherical caps"),
            Certificate.CapsuleMaximum-Certificate.CapsuleMinimum>=84-1.e-8);
        Disagreements+=Without&&!With;
    }
    auto Full=TriangleMesh(Vertices);Chaos::FMTDInfo FullMtd{};
    TestTrue(TEXT("Installed no-MTD triangle path reproduces the historical diagnostic contact"),Full->OverlapGeom(Capsule,Pose,0,nullptr));
    TestFalse(TEXT("All eight authored cooked faces have no native GJK penetration"),Full->OverlapGeom(Capsule,Pose,0,&FullMtd));
    TestTrue(TEXT("The diagnostic narrows the divergent path to an individual cooked face"),Disagreements>0);

    const auto Control=[&](const TCHAR* Label,const TArray<FVector>& Points,bool Expected)
    {
        auto Mesh=TriangleMesh(Points);Chaos::FMTDInfo Mtd{};
        TestEqual(Label,Mesh->OverlapGeom(Capsule,Pose,0,nullptr),Expected);
        TestEqual(Label,Mesh->OverlapGeom(Capsule,Pose,0,&Mtd),Expected);
        if (Expected) TestTrue(TEXT("Real obstruction retains positive native penetration"),Mtd.Penetration>0);
        const auto Certificate=WarCitadelCookedContacts::TriangleSeparation(Center-FVector(0,0,54),Center+FVector(0,0,54),42,
            Points[0],Points[1],Points[2]);
        TestEqual(TEXT("Geometric certificate never clears the real obstruction controls"),Certificate.Certified,!Expected);
    };
    Control(TEXT("Real wall blocks both native query paths"),{
        Center+FVector(20,-500,-500),Center+FVector(20,500,-500),Center+FVector(20,0,500)},true);
    Control(TEXT("Real ceiling blocks the complete capsule in both native query paths"),{
        Center+FVector(-500,-500,90),Center+FVector(500,-500,90),Center+FVector(0,500,90)},true);
    Control(TEXT("Native resting floor clears the complete capsule in both native query paths"),{
        Center+FVector(-500,-500,-98.4),Center+FVector(500,-500,-98.4),Center+FVector(0,500,-98.4)},false);
    const FVector Start(0,0,-54),End(0,0,54);
    for (double Z:{96.,95.9999,96.0001})
        TestFalse(TEXT("Tangent, shallow penetration and uncertain near-zero separation cannot be certified"),
            WarCitadelCookedContacts::TriangleSeparation(Start,End,42,FVector(-100,-100,Z),FVector(100,-100,Z),FVector(0,100,Z)).Certified);
    TestFalse(TEXT("Degenerate geometry remains unresolved"),
        WarCitadelCookedContacts::TriangleSeparation(Start,End,42,FVector(0,0,200),FVector(1,0,200),FVector(2,0,200)).Certified);
    TestFalse(TEXT("Near-degenerate geometry remains unresolved"),
        WarCitadelCookedContacts::TriangleSeparation(Start,End,42,FVector(0,0,200),FVector(100,0,200),FVector(50,1.e-8,200)).Certified);
    const FTransform Rotated(FRotator(23,47,11),FVector(900000,-800000,700000));
    const FVector FarA=Rotated.TransformPosition(FVector(-200,-200,120));
    const FVector FarB=Rotated.TransformPosition(FVector(200,-200,120));
    const FVector FarC=Rotated.TransformPosition(FVector(0,200,120));
    const auto Far=WarCitadelCookedContacts::TriangleSeparation(Rotated.TransformPosition(Start),Rotated.TransformPosition(End),42,FarA,FarB,FarC);
    const auto Reversed=WarCitadelCookedContacts::TriangleSeparation(Rotated.TransformPosition(Start),Rotated.TransformPosition(End),42,FarC,FarB,FarA);
    TestTrue(TEXT("Rigidly rotated large-world clearance remains certifiable above its enlarged numerical guard"),Far.Certified);
    TestTrue(TEXT("Winding reversal retains the same complete-object plane gap"),FMath::Abs(Far.SeparatingPlaneGapCm-Reversed.SeparatingPlaneGapCm)<1.e-8);
    TestTrue(TEXT("World-coordinate magnitude increases the conservative uncertainty guard"),Far.NumericalGuardCm>3);
    return true;
}
#endif
