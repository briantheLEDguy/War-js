#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarT1NavigationAuthoringLibrary.h"
#include "Engine/World.h"
#include "Engine/Level.h"
#include "WarZoneAnchor.h"
#include <limits>
#include "WarT1NavigationPrismBuilder.h"
#include "ActorFactories/ActorFactory.h"
#include "NavModifierVolume.h"
#include "Components/BrushComponent.h"
#include "PhysicsEngine/BodySetup.h"
#include "Model.h"
#include "Engine/Polys.h"
#include "Algo/Reverse.h"

namespace
{
    double Area(const TArray<FVector2D>& P)
    {
        double Result=0;for (int32 I=0;I<P.Num();++I) Result+=P[I].X*P[(I+1)%P.Num()].Y-P[I].Y*P[(I+1)%P.Num()].X;
        return FMath::Abs(Result)*.5;
    }
    bool Inside(FVector2D P,const TArray<FVector2D>& Polygon)
    {
        bool Result=false;
        for (int32 I=0,J=Polygon.Num()-1;I<Polygon.Num();J=I++)
        {
            const auto A=Polygon[J],B=Polygon[I];
            if ((A.Y>P.Y)!=(B.Y>P.Y) && P.X<(B.X-A.X)*(P.Y-A.Y)/(B.Y-A.Y)+A.X) Result=!Result;
        }
        return Result;
    }
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarT1NavigationFootprintTest,"AegisWar.Foundation.T1NavigationFootprint",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarT1NavigationFootprintTest::RunTest(const FString& Parameters)
{
    const FBox2D Bounds(FVector2D(0,0),FVector2D(1000,800));FString Error;TArray<TArray<FVector2D>> Cells;
    const TArray<FVector2D> Concave{{100,100},{900,100},{900,700},{600,700},{600,300},{400,300},{400,700},{100,700}};
    TestTrue(TEXT("Concave footprint partitions"),UWarT1NavigationAuthoringLibrary::ExteriorCells(Bounds,Concave,Cells,Error));
    double Exterior=0;
    for (const auto& Cell:Cells)
    {
        TestTrue(TEXT("Every exclusion is a convex prism base"),Cell.Num()>=3 && Cell.Num()<=4);
        Exterior+=Area(Cell);FVector2D Center=FVector2D::ZeroVector;for (auto P:Cell) Center+=P;Center/=Cell.Num();
        TestFalse(TEXT("Exclusion centroid is outside the playable concavity"),Inside(Center,Concave));
        for (int32 I=0;I<Cell.Num();++I)
        {
            const auto A=Cell[(I+1)%Cell.Num()]-Cell[I],B=Cell[(I+2)%Cell.Num()]-Cell[(I+1)%Cell.Num()];
            TestTrue(TEXT("Exclusion winding remains convex"),A.X*B.Y-A.Y*B.X>=-1e-6);
        }
    }
    TestTrue(TEXT("Exact complement area, including inward bay"),FMath::IsNearlyEqual(Exterior+Area(Concave),800000.,1e-6));
    for (double Y=17;Y<800;Y+=31) for (double X=13;X<1000;X+=29)
    {
        int32 Covers=0;for (const auto& Cell:Cells) Covers+=Inside({X,Y},Cell) ? 1 : 0;
        TestEqual(TEXT("Exterior is covered once, playable ground never excluded"),Covers,Inside({X,Y},Concave) ? 0 : 1);
    }
    FBox2D Sampled;
    const FBox2D DistantOwnership(FVector2D(-360000,-340000),FVector2D(360000,340000));
    TestTrue(TEXT("Distant scenery does not expand navigation"),UWarT1NavigationAuthoringLibrary::NavigationBounds(DistantOwnership,Concave,Sampled,Error));
    TestTrue(TEXT("Navigation bounds equal the playable envelope"),Sampled.Min.Equals(FVector2D(100,100)) && Sampled.Max.Equals(FVector2D(900,700)));
    TestTrue(TEXT("Legacy rectangle retains its own envelope"),UWarT1NavigationAuthoringLibrary::NavigationBounds(Bounds,{{0,0},{1000,0},{1000,800},{0,800}},Sampled,Error));
    TestTrue(TEXT("Legacy rectangle bounds are exact"),Sampled.Min.Equals(Bounds.Min) && Sampled.Max.Equals(Bounds.Max));
    TestFalse(TEXT("Ownership must contain navigation"),UWarT1NavigationAuthoringLibrary::NavigationBounds(Bounds,{{0,0},{1001,0},{0,800}},Sampled,Error));
    TestFalse(TEXT("Rejected bounds leave no partial extent"),Sampled.bIsValid);
    TestFalse(TEXT("Playable navigation keeps the original size limit"),UWarT1NavigationAuthoringLibrary::NavigationBounds(DistantOwnership,{{-300000,0},{300000,0},{0,10000}},Sampled,Error));
    auto Reverse=Concave;Algo::Reverse(Reverse);
    TestTrue(TEXT("Opposite outline winding is supported"),UWarT1NavigationAuthoringLibrary::ExteriorCells(Bounds,Reverse,Cells,Error));
    const TArray<FVector2D> Skew{{40,80},{850,20},{950,600},{500,350},{100,750}};
    TestTrue(TEXT("Sloping concave edges partition"),UWarT1NavigationAuthoringLibrary::ExteriorCells(Bounds,Skew,Cells,Error));
    Exterior=0;for (const auto& Cell:Cells) Exterior+=Area(Cell);
    TestTrue(TEXT("Sloping exterior retains exact area"),FMath::IsNearlyEqual(Exterior+Area(Skew),800000.,1e-6));
    const TArray<FVector2D> Rectangle{{0,0},{1000,0},{1000,800},{0,800}};
    TestTrue(TEXT("Legacy rectangular footprint needs no exclusions"),UWarT1NavigationAuthoringLibrary::ExteriorCells(Bounds,Rectangle,Cells,Error));
    TestTrue(TEXT("Full content rectangle has empty exterior"),Cells.IsEmpty());
    for (const TArray<FVector2D>& Invalid:TArray<TArray<FVector2D>>{
        {{100,100},{900,700},{900,100},{100,700}},{{100,100},{100,100},{200,200}},
        {{100,100},{1001,100},{500,700}},{{100,100},{std::numeric_limits<double>::infinity(),100},{500,700}},
        {{100,100},{200,200},{300,300}}})
    {
        TestFalse(TEXT("Malformed outline is rejected"),UWarT1NavigationAuthoringLibrary::ExteriorCells(Bounds,Invalid,Cells,Error));
        TestTrue(TEXT("Rejection retains no partial exclusions"),Cells.IsEmpty());TestFalse(TEXT("Rejection explains why"),Error.IsEmpty());
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarT1NavigationIsolationTest,"AegisWar.Foundation.T1NavigationIsolation",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarT1NavigationIsolationTest::RunTest(const FString& Parameters)
{
    const auto Admit=&UWarT1NavigationAuthoringLibrary::IsPrivateCandidate;
    const FName Zone=TEXT("sunmeadow_march");
    const FString Root=TEXT("/Game/WorldRebuild/T1Redesign_Atmosphere_123456abcdef_Navigation/");
    TestTrue(TEXT("Exact private regional candidate is admitted"),Admit(Root+TEXT("sunmeadow_march/Review"),Zone));
    for (const FString& Package:TArray<FString>{TEXT("/Game/Capitals/AegisCapital"),Root+TEXT("sunmeadow_march/Generated"),
        Root+TEXT("cinderfen_outskirts/Review"),TEXT("/Game/WorldRebuild/T1Redesign_Atmosphere_123_Navigation/sunmeadow_march/Review"),
        TEXT("/Game/WorldRebuild/T1Redesign_Atmosphere_123456abcdeG_Navigation/sunmeadow_march/Review")})
        TestFalse(TEXT("Owner maps, another region and malformed revisions are rejected"),Admit(Package,Zone));
    TestFalse(TEXT("Non-T1 region is rejected"),Admit(Root+TEXT("aegis_capital/Review"),TEXT("aegis_capital")));
    const auto Init=UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false)
        .CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::Editor,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Init);
    if (!TestNotNull(TEXT("Unowned world guard fixture"),World)) return false;
    auto* Existing=World->SpawnActor<AWarZoneAnchor>();const int32 Count=World->PersistentLevel->Actors.Num();
    const bool Dirty=World->GetOutermost()->IsDirty();
    const FString Result=UWarT1NavigationAuthoringLibrary::BuildNavigation(World,Zone,{},-1000,20000);
    TestTrue(TEXT("Rejected authoring reports failure"),Result.Contains(TEXT("\"passed\": false")));
    TestEqual(TEXT("Rejected operation preserves actors"),World->PersistentLevel->Actors.Num(),Count);
    TestEqual(TEXT("Rejected operation preserves package state"),World->GetOutermost()->IsDirty(),Dirty);
    TestTrue(TEXT("Owner anchor remains in its level"),Existing->GetLevel()==World->PersistentLevel);
    World->DestroyWorld(false);return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarT1NavigationProbeGuardTest,"AegisWar.Foundation.T1NavigationProbeGuards",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarT1NavigationProbeGuardTest::RunTest(const FString& Parameters)
{
    TestTrue(TEXT("Missing authoring world is rejected"),UWarT1NavigationAuthoringLibrary::BuildNavigation(nullptr,TEXT("sunmeadow_march"),{},0,1000).Contains(TEXT("\"passed\": false")));
    TestTrue(TEXT("Missing navigation never falls back to another agent"),UWarT1NavigationAuthoringLibrary::ProbeRoute(nullptr,TEXT("sunmeadow_march"),true,{{0,0,0},{100,0,0}}).Contains(TEXT("\"passed\": false")));
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarT1NavigationPrismTest,"AegisWar.Foundation.T1NavigationPrism",
    EAutomationTestFlags::EditorContext|EAutomationTestFlags::EngineFilter)
bool FWarT1NavigationPrismTest::RunTest(const FString& Parameters)
{
    const auto Init=UWorld::InitializationValues().AllowAudioPlayback(false).RequiresHitProxies(false)
        .CreatePhysicsScene(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::Editor,false,NAME_None,nullptr,true,ERHIFeatureLevel::Num,&Init);
    if (!TestNotNull(TEXT("Transient prism geometry fixture"),World)) return false;
    for (const TArray<FVector2D>& Hull:TArray<TArray<FVector2D>>{
        {{-100,-100},{100,-100},{60,100},{-80,100}},{{-100,-100},{100,-100},{0,100}}})
    {
        auto* Volume=World->SpawnActor<ANavModifierVolume>();auto* Builder=NewObject<UWarT1NavigationPrismBuilder>();
        Builder->Hull=Hull;Builder->HalfHeight=300;UActorFactory::CreateBrushForVolumeActor(Volume,Builder);
        TestNotNull(TEXT("Serialized brush exists"),Volume->Brush.Get());
        if (Volume->Brush && Volume->Brush->Polys)
        {
            TestEqual(TEXT("Prism has both caps and every side"),Volume->Brush->Polys->Element.Num(),Hull.Num()+2);
            for (const FPoly& Poly:Volume->Brush->Polys->Element)
                TestTrue(TEXT("Every prism face has a finite unit normal"),!Poly.Normal.ContainsNaN() && FMath::IsNearlyEqual(Poly.Normal.Size(),1.f,1e-4f));
        }
        const auto* Body=Volume->GetBrushComponent()->GetBodySetup();
        TestTrue(TEXT("Native convex modifier shape is present"),Body && !Body->AggGeom.ConvexElems.IsEmpty());
        TestTrue(TEXT("Navigation exclusion adds no physical collision"),Volume->GetBrushComponent()->GetCollisionEnabled()==ECollisionEnabled::NoCollision);
        const auto* SavedBuilder=Cast<UWarT1NavigationPrismBuilder>(Volume->BrushBuilder);
        TestTrue(TEXT("Build recipe retains exact hull on the actor"),SavedBuilder && SavedBuilder->Hull==Hull);
    }
    auto* Invalid=NewObject<UWarT1NavigationPrismBuilder>();Invalid->HalfHeight=300;
    for (const TArray<FVector2D>& Hull:TArray<TArray<FVector2D>>{
        {{0,0},{0,100},{100,0}},{{0,0},{100,0},{20,20},{0,100}},{{0,0},{0,0},{100,100}},
        {{0,0},{std::numeric_limits<double>::quiet_NaN(),0},{0,100}}})
    {
        Invalid->Hull=Hull;TestFalse(TEXT("Malformed exclusion recipe is rejected before brush mutation"),Invalid->Build(nullptr,nullptr));
    }
    World->DestroyWorld(false);return true;
}
#endif
