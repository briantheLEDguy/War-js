#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarWorldEditCatalog.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarWorldEditCatalogTest, "AegisWar.Foundation.WorldEditCatalog",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarWorldEditCatalogTest::RunTest(const FString& Parameters)
{
    const FString House = TEXT("/Game/Imported/aegis_house_1.aegis_house_1:source-a");
    const FString Rowhouse = TEXT("/Game/Imported/aegis_rowhouse_2.aegis_rowhouse_2:source-b");
    TArray<FWarWorldEditObject> Baseline = {
        { TEXT("house_z"), FTransform::Identity, false, House },
        { TEXT("rowhouse"), FTransform::Identity, false, Rowhouse },
        { TEXT("house_a"), FTransform::Identity, false, House },
        { TEXT("created"), FTransform::Identity, false, House, TEXT("house_a") }
    };
    const auto Entries = WarWorldEditCatalog::Build(Baseline);
    TestEqual(TEXT("Repeated placements and created objects do not duplicate models"), Entries.Num(), 2);
    if (Entries.Num() != 2) return false;
    TestEqual(TEXT("Stable template identity"), Entries[0].TemplateId, FName(TEXT("house_a")));
    TestEqual(TEXT("Friendly model label"), Entries[0].Label, FString(TEXT("House 1")));
    TestEqual(TEXT("Whitespace query retains all models"), WarWorldEditCatalog::Filter(Entries, TEXT("  \t ")).Num(), 2);
    const auto Filtered = WarWorldEditCatalog::Filter(Entries, TEXT("  ROWHOUSE  2 "));
    TestEqual(TEXT("Case-insensitive multi-term search"), Filtered.Num(), 1);
    if (Filtered.Num() == 1) TestEqual(TEXT("Search retains the trusted template"), Filtered[0].TemplateId, FName(TEXT("rowhouse")));
    TestEqual(TEXT("All search terms must match"), WarWorldEditCatalog::Filter(Entries, TEXT("house 9")).Num(), 0);
    Swap(Baseline[0], Baseline[2]);
    TestEqual(TEXT("Enumeration order does not change the template"), WarWorldEditCatalog::Build(Baseline)[0].TemplateId, Entries[0].TemplateId);
    Baseline.Add({ TEXT("kit_floor"), FTransform::Identity, false,
        TEXT("/Game/LicensedKits/MH2/SM_MH_02_Stone_Floor_01.SM_MH_02_Stone_Floor_01:kit-source") });
    const auto Kit = WarWorldEditCatalog::Filter(WarWorldEditCatalog::Build(Baseline), TEXT("town floor"));
    TestEqual(TEXT("Purchased modular pieces have searchable player-facing labels"), Kit.Num(), 1);
    if (Kit.Num() == 1) TestEqual(TEXT("Kit label"), Kit[0].Label, FString(TEXT("Town kit Stone Floor 01")));
    return true;
}
#endif
