#pragma once
#include "CoreMinimal.h"

namespace WarWorldEditMap
{
    inline bool IsCitadelCampaign(const FString& Package)
    {
        const FString Prefix = TEXT("/Game/WorldRebuild/AegisCitadel_");
        const FString Suffix = TEXT("/CampaignCandidate");
        if (!Package.StartsWith(Prefix) || !Package.EndsWith(Suffix)
            || Package.Len() != Prefix.Len() + 12 + Suffix.Len()) return false;
        for (TCHAR C : Package.Mid(Prefix.Len(),12))
            if (!((C >= TEXT('0') && C <= TEXT('9')) || (C >= TEXT('a') && C <= TEXT('f')))) return false;
        return true;
    }
    // Map selection never grants authority; the caller still enforces standalone GM access.
    inline bool IsSupported(const FString& Package, const FString& SelectedMap)
    {
        return Package == TEXT("/Game/Capitals/aegis_capital/AegisCapital_Workbench")
            || Package == TEXT("/Game/Capitals/Siege/AegisCapital_Siege")
            || Package == TEXT("/Game/Capitals/kit_pilot/AegisCapital_Workbench")
            || Package == TEXT("/Game/Capitals/crownward/AegisCapital_Workbench")
            || (SelectedMap.StartsWith(TEXT("/Game/Capitals/crownward/")) && Package == SelectedMap)
            || (SelectedMap.StartsWith(TEXT("/Game/WorldRebuild/DutchBastion_"))
                && SelectedMap.EndsWith(TEXT("/Bastion_Campaign_v3")) && Package == SelectedMap)
            || (IsCitadelCampaign(SelectedMap) && Package == SelectedMap);
    }
}
