#include "WarContentSubsystem.h"
#include "Dom/JsonObject.h"

FString UWarContentSubsystem::GetCityTeachingText(const FName Service) const
{
    if (!bReady || !Manifest.IsValid()) return TEXT("Teaching catalog is unavailable.");
    FString Text;
    if (Service == TEXT("craft_teacher"))
    {
        Text = TEXT("Use the crafting tables in Cinderbank. Professions advance through practice; this teacher does not sell ranks.\n\n");
        const auto Craft = Manifest->GetObjectField(TEXT("crafting"));
        for (const auto& Value : Craft->GetArrayField(TEXT("professions")))
        {
            const auto Row = Value->AsObject();
            Text += Row->GetStringField(TEXT("label")) + TEXT(": ") + Row->GetStringField(TEXT("description")) + TEXT("\n\n");
        }
        for (const auto Id : GetCraftRecipeIds())
        {
            FWarCraftRecipe Recipe; FString Error;
            if (GetCraftRecipe(Id, Recipe, Error))
                Text += FString::Printf(TEXT("%s — %s, rank %d, station: %s\n"), *Recipe.Name,
                    *Recipe.Profession.ToString(), Recipe.MinimumRank, *Recipe.Station.ToString());
        }
    }
    else if (Service == TEXT("class_teacher"))
    {
        Text = TEXT("Abilities follow your class and level; no training purchase is required. The entries below describe the source gameplay catalog; full native class execution remains in development.\n\n");
        const auto Abilities = Manifest->GetObjectField(TEXT("abilities"));
        TMap<FString, TSharedPtr<FJsonObject>> Progress;
        for (const auto& Value : Abilities->GetArrayField(TEXT("progression")))
        { const auto Row = Value->AsObject(); Progress.Add(Row->GetStringField(TEXT("abilityId")), Row); }
        for (const auto& Value : Abilities->GetArrayField(TEXT("kits")))
        {
            const auto Kit = Value->AsObject();
            Text += Kit->GetStringField(TEXT("career")) + TEXT(" — ") + Kit->GetObjectField(TEXT("resource"))->GetStringField(TEXT("label")) + TEXT("\n");
            for (const auto& Ability : Kit->GetArrayField(TEXT("abilities")))
            {
                const auto Row = Ability->AsObject();
                const auto* Unlock = Progress.Find(Row->GetStringField(TEXT("id")));
                if (!Unlock) continue;
                Text += FString::Printf(TEXT("Level %d: %s%s\n"), (*Unlock)->GetIntegerField(TEXT("unlockLevel")),
                    *Row->GetStringField(TEXT("name")), (*Unlock)->GetBoolField(TEXT("activatable")) ? TEXT("") : TEXT(" (unavailable)"));
            }
            Text += TEXT("\n");
        }
    }
    else Text = TEXT("The vault is staffed, but banking transactions are not available yet.");
    return Text;
}
