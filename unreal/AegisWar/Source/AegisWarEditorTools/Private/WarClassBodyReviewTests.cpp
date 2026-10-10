#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarImportLibrary.h"
#include "WarCharacterVisualDefinition.h"
#include "Engine/StaticMesh.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarClassBodyEquipmentResetTest, "AegisWar.Foundation.ClassBodyEquipmentReset",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarClassBodyEquipmentResetTest::RunTest(const FString& Parameters)
{
    TestFalse(TEXT("Missing visual is rejected"), UWarImportLibrary::ClearClassBodyEquipment(nullptr));
    auto* Visual = NewObject<UWarCharacterVisualDefinition>();
    Visual->ProfileKey = TEXT("civic_battle_prelate_m");
    TestFalse(TEXT("Legacy equipment is preserved"), UWarImportLibrary::ClearClassBodyEquipment(Visual));
    Visual->ClassId = TEXT("hex_inquisitor"); Visual->BodyVariant = TEXT("f");
    Visual->SourceSha256 = FString::ChrN(64, TEXT('a'));
    Visual->ProfileKey = TEXT("classbody_hex_inquisitor_f_aaaaaaaaaaaa");
    Visual->PlayableProfileKey = TEXT("civic_hex_inquisitor_f");
    Visual->WeaponMesh = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(TEXT("/Game/Unloaded/Weapon.Weapon")));
    Visual->ShieldMesh = TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(TEXT("/Game/Unloaded/Shield.Shield")));
    TestFalse(TEXT("Unloaded equipment still owns a serialized path"), Visual->WeaponMesh.IsNull());
    TestTrue(TEXT("Own body revision clears unloaded equipment paths"), UWarImportLibrary::ClearClassBodyEquipment(Visual));
    TestTrue(TEXT("Weapon soft path is empty"), Visual->WeaponMesh.IsNull());
    TestTrue(TEXT("Shield soft path is empty"), Visual->ShieldMesh.IsNull());
    return true;
}
#endif
