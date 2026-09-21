#include "WarPlayerState.h"
#include "WarAttributeSet.h"
#include "WarContentSubsystem.h"
#include "Engine/GameInstance.h"
#include "Misc/DateTime.h"

namespace
{
    int64 ServerUtcMs() { return (FDateTime::UtcNow() - FDateTime(1970, 1, 1)).GetTicks() / ETimespan::TicksPerMillisecond; }
}

bool AWarPlayerState::PlantSeed(const FName SeedKey, const bool bUseSoil, const int32 ExpectedRevision, FString& Error)
{
    if (!HasAuthority() || ExpectedRevision != Inventory.Revision || !GetPawn() || Attributes->GetHealth() <= 0.f)
    { Error = TEXT("Planting is unavailable or inventory changed."); return false; }
    const auto* Content = GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarContentSubsystem>() : nullptr;
    FWarCultivationSeed Seed;
    if (!Content) { Error = TEXT("Cultivation catalog is unavailable."); return false; }
    if (!Content->GetCultivationSeed(SeedKey, Seed, Error)
        || !WarCultivation::Plant(Inventory, Seed, bUseSoil, ServerUtcMs(), FGuid::NewGuid(), Error)) return false;
    ForceNetUpdate(); return true;
}

bool AWarPlayerState::HarvestCrop(const FGuid PlotId, const int32 ExpectedRevision, FString& Error)
{
    if (!HasAuthority() || ExpectedRevision != Inventory.Revision || !GetPawn() || Attributes->GetHealth() <= 0.f)
    { Error = TEXT("Harvesting is unavailable or inventory changed."); return false; }
    const auto* Plot = Inventory.CultivationPlots.FindByPredicate([PlotId](const auto& Row) { return Row.Id == PlotId; });
    const auto* Content = GetGameInstance() ? GetGameInstance()->GetSubsystem<UWarContentSubsystem>() : nullptr;
    FWarCultivationSeed Seed;
    if (!Content || !Plot) { Error = TEXT("Crop or cultivation catalog is unavailable."); return false; }
    if (!Content->GetCultivationSeed(Plot->SeedKey, Seed, Error)
        || !WarCultivation::Harvest(Inventory, Seed, PlotId, ServerUtcMs(), Error)) return false;
    ForceNetUpdate(); return true;
}

void AWarPlayerState::ServerPlantSeed_Implementation(const FName SeedKey, const bool bUseSoil, const int32 ExpectedRevision)
{
    FString Error; const bool Accepted = PlantSeed(SeedKey, bUseSoil, ExpectedRevision, Error); ClientInventoryResult(Accepted, Error);
}
void AWarPlayerState::ServerHarvestCrop_Implementation(const FGuid PlotId, const int32 ExpectedRevision)
{
    FString Error; const bool Accepted = HarvestCrop(PlotId, ExpectedRevision, Error); ClientInventoryResult(Accepted, Error);
}
