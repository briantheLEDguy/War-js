#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarNpcEquipment.h"
#include "WarRuntimeSettings.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarNpcEquipmentTest, "AegisWar.Foundation.CombatNpcEquipment",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarNpcEquipmentTest::RunTest(const FString& Parameters)
{
    auto* Catalog = GetDefault<UWarRuntimeSettings>()->NpcEquipmentCatalog.LoadSynchronous();
    if (!TestNotNull(TEXT("Saved equipment catalog exists"), Catalog)) return false;
    const FName Profile(TEXT("enemy_aegis_campaign_raider_raider")), Identity(TEXT("sunmeadow_march_west_raider_1"));
    const FWarNpcLoadout* Binding = nullptr; FString Error;
    if (!TestTrue(TEXT("Exact source raider is armed"), Catalog->Resolve(Profile, Identity, TEXT("enemy"), Binding, Error))) return false;
    TestTrue(TEXT("Guard requires weapons"), UWarNpcEquipmentLibrary::RequiresWeapons(TEXT("guard")));
    TestTrue(TEXT("Marshal requires weapons"), UWarNpcEquipmentLibrary::RequiresWeapons(TEXT("marshal")));
    TestFalse(TEXT("Civilian does not inherit a weapon"), UWarNpcEquipmentLibrary::RequiresWeapons(TEXT("resident")));
    const FWarNpcLoadout Original = *Binding;
    auto* Invalid = NewObject<UWarNpcEquipmentCatalog>(); Invalid->Loadouts = {Original};
    TestFalse(TEXT("Unreviewed identity rejected"), Invalid->Resolve(Profile, TEXT("other"), TEXT("enemy"), Binding, Error));
    Invalid->Loadouts.Add(Original);
    TestFalse(TEXT("Duplicate bindings rejected"), Invalid->Resolve(Profile, Identity, TEXT("enemy"), Binding, Error));
    Invalid->Loadouts = {Original}; Invalid->Loadouts[0].Attachments.Reset();
    TestFalse(TEXT("Unarmed humanoid rejected"), Invalid->Resolve(Profile, Identity, TEXT("enemy"), Binding, Error));
    Invalid->Loadouts = {Original}; Invalid->Loadouts[0].Attachments[0].Bone = NAME_None;
    TestFalse(TEXT("Missing grip rejected"), Invalid->Resolve(Profile, Identity, TEXT("enemy"), Binding, Error));
    Invalid->Loadouts = {Original}; Invalid->Loadouts[0].BodySourceSha256 = TEXT("stale");
    TestFalse(TEXT("Missing provenance rejected"), Invalid->Resolve(Profile, Identity, TEXT("enemy"), Binding, Error));

    const auto Values = UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false)
        .CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false);
    UWorld* World = UWorld::CreateWorld(EWorldType::Game, false, NAME_None, nullptr, true, ERHIFeatureLevel::Num, &Values);
    if (!TestNotNull(TEXT("Equipment test world"), World)) return false;
    auto* Actor = World->SpawnActor<AActor>();
    auto* Body = NewObject<USkeletalMeshComponent>(Actor); Actor->SetRootComponent(Body);
    Body->SetSkeletalMesh(Original.Body.LoadSynchronous()); Body->RegisterComponent();
    TestTrue(TEXT("Actual native equipment attaches"), UWarNpcEquipmentLibrary::Apply(Body, Profile, Identity, TEXT("enemy"), Error));
    TestTrue(TEXT("Reload is idempotent"), UWarNpcEquipmentLibrary::Apply(Body, Profile, Identity, TEXT("enemy"), Error));
    TInlineComponentArray<UStaticMeshComponent*> Components; Actor->GetComponents(Components);
    int32 Weapons = 0;
    for (const auto* Component : Components)
    {
        if (!Component->ComponentHasTag(TEXT("WarNpcEquipment"))) continue;
        ++Weapons;
        TestTrue(TEXT("Weapon follows animated body"), Component->GetAttachParent() == Body);
        TestTrue(TEXT("Weapon has a real bone"), Body->DoesSocketExist(Component->GetAttachSocketName()));
        TestEqual(TEXT("Weapon cannot obstruct landing or strikes"), Component->GetCollisionEnabled(), ECollisionEnabled::NoCollision);
        TestTrue(TEXT("Generated attachment is transient"), Component->HasAnyFlags(RF_Transient));
    }
    TestEqual(TEXT("No duplicate weapons on repeated preparation"), Weapons, Original.Attachments.Num());
    Body->SetSkeletalMesh(nullptr);
    TestFalse(TEXT("Mismatched body cannot reuse a loadout"), UWarNpcEquipmentLibrary::Apply(Body, Profile, Identity, TEXT("enemy"), Error));
    World->DestroyWorld(false);
    return true;
}
#endif
