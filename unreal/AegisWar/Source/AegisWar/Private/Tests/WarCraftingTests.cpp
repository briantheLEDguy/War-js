#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "WarContentSubsystem.h"
#include "WarCraftingRules.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarCraftingTest, "AegisWar.Foundation.CraftingCatalogAndRules",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarCraftingTest::RunTest(const FString& Parameters)
{
    FString Json;
    if (!TestTrue(TEXT("Staged browser catalog exists"), FFileHelper::LoadFileToString(Json,
        *FPaths::Combine(FPaths::ProjectContentDir(), TEXT("Migration/content.json"))))) return false;
    TSharedPtr<FJsonObject> Root;
    if (!TestTrue(TEXT("Catalog parses"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root))) return false;
    const auto& Recipes = Root->GetObjectField(TEXT("crafting"))->GetArrayField(TEXT("recipes"));
    TestEqual(TEXT("All five current recipes tested"), Recipes.Num(), 5);
    for (const auto& Value : Recipes)
    {
        const FName Id(*Value->AsObject()->GetStringField(TEXT("id")));
        FWarCraftRecipe Recipe; FString Error;
        if (!TestTrue(Id.ToString(), UWarContentSubsystem::ParseCraftRecipe(Root, Id, Recipe, Error))) continue;
        TArray<FWarInventoryItem> Items;
        for (const auto& Entry : Recipe.Inputs)
        {
            FWarInventoryItem Item;
            Item.Key = Entry.Key; Item.Quantity = Entry.Value; Item.Kind = TEXT("misc"); Item.Slot = Items.Num();
            Items.Add(Item);
        }
        TMap<int32, int32> Selected;
        const int32 Xp = (Recipe.MinimumRank - 1) * 100;
        TestTrue(TEXT("Portable recipe has browser eligibility"), WarCrafting::SelectIngredients(Recipe, NAME_None, Xp, Items, Selected, Error));
        TestEqual(TEXT("Every required ingredient selected"), Selected.Num(), Items.Num());
        for (const auto& Item : Items) TestEqual(TEXT("Exact input quantity"), Selected.FindRef(Item.Slot), Item.Quantity);
        TestTrue(TEXT("General station accepts recipe"), WarCrafting::SelectIngredients(Recipe, TEXT("general"), Xp, Items, Selected, Error));
        TestTrue(TEXT("Matching station accepts recipe"), WarCrafting::SelectIngredients(Recipe, Recipe.Station, Xp, Items, Selected, Error));
        TestFalse(TEXT("Wrong specialist rejects recipe"), WarCrafting::SelectIngredients(Recipe, TEXT("wrong_station"), Xp, Items, Selected, Error));
        if (Recipe.MinimumRank > 1)
            TestFalse(TEXT("Rank gate precedes consumption"), WarCrafting::SelectIngredients(Recipe, NAME_None, Xp - 1, Items, Selected, Error));
        Items.Pop();
        TestFalse(TEXT("Missing ingredient rejects recipe"), WarCrafting::SelectIngredients(Recipe, NAME_None, Xp, Items, Selected, Error));
    }
    TestEqual(TEXT("Rank starts at one"), WarCrafting::RankForXp(0), 1);
    TestEqual(TEXT("99 XP remains rank one"), WarCrafting::RankForXp(99), 1);
    TestEqual(TEXT("100 XP reaches rank two"), WarCrafting::RankForXp(100), 2);
    FWarCraftRecipe Missing; FString Error;
    TestFalse(TEXT("Unknown recipe cannot be fabricated"), UWarContentSubsystem::ParseCraftRecipe(Root, TEXT("client_invented"), Missing, Error));
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarSalvageTest, "AegisWar.Foundation.SalvageParity",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FWarSalvageTest::RunTest(const FString& Parameters)
{
    FString Json;
    if (!TestTrue(TEXT("Browser salvage fixture exists"), FFileHelper::LoadFileToString(Json,
        *FPaths::Combine(FPaths::ProjectDir(), TEXT("../../migration/fixtures/salvage.json"))))) return false;
    TSharedPtr<FJsonObject> Root;
    if (!TestTrue(TEXT("Fixture parses"), FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root))) return false;
    const auto& Cases = Root->GetArrayField(TEXT("cases"));
    TestEqual(TEXT("All browser salvage variants execute"), Cases.Num(), 25);
    for (const auto& Value : Cases)
    {
        const auto Row = Value->AsObject();
        const auto Source = Row->GetObjectField(TEXT("item"));
        FWarInventoryItem Item;
        Item.Key = FName(*Source->GetStringField(TEXT("key")));
        Item.Kind = FName(*Source->GetStringField(TEXT("kind")));
        Item.EquipSlot = FName(*Source->GetStringField(TEXT("equipSlot")));
        const TSharedPtr<FJsonObject>* Affix = nullptr;
        if (Source->TryGetObjectField(TEXT("affix"), Affix))
        { Item.bHasAffix = true; Item.StrengthBonus = (*Affix)->GetIntegerField(TEXT("strengthBonus")); }
        TArray<FWarInventoryItem> Outputs; FString Error;
        TestTrue(Row->GetStringField(TEXT("name")), WarCrafting::SalvageOutputs(Item, Outputs, Error));
        const auto& Expected = Row->GetArrayField(TEXT("expected"));
        if (!TestEqual(TEXT("All output entries match"), Outputs.Num(), Expected.Num())) continue;
        for (int32 Index = 0; Index < Outputs.Num(); ++Index)
        {
            TestEqual(TEXT("Output identity"), Outputs[Index].Key.ToString(), Expected[Index]->AsObject()->GetStringField(TEXT("key")));
            TestEqual(TEXT("Output quantity"), Outputs[Index].Quantity, Expected[Index]->AsObject()->GetIntegerField(TEXT("qty")));
        }
    }
    FWarInventoryItem Invalid; Invalid.Kind = TEXT("consumable");
    TArray<FWarInventoryItem> Outputs; FString Error;
    TestFalse(TEXT("Consumables cannot become salvage materials"), WarCrafting::SalvageOutputs(Invalid, Outputs, Error));
    Invalid.Kind = TEXT("weapon"); Invalid.Quantity = 2;
    TestFalse(TEXT("Malformed gear stack cannot be salvaged"), WarCrafting::SalvageOutputs(Invalid, Outputs, Error));
    return true;
}
#endif
