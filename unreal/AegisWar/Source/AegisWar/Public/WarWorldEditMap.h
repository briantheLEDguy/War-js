#pragma once
#include "CoreMinimal.h"
#include "Misc/DateTime.h"

namespace WarWorldEditMap
{
    inline bool IsCitadelHumanReview(const FString& Package)
    {
        const FString Prefix = TEXT("/Game/WorldRebuild/CitadelHumanReview_");
        const FString Suffix = TEXT("/Walkthrough");
        if (!Package.StartsWith(Prefix, ESearchCase::CaseSensitive)
            || !Package.EndsWith(Suffix, ESearchCase::CaseSensitive)) return false;
        const FString Revision = Package.Mid(Prefix.Len(), Package.Len() - Prefix.Len() - Suffix.Len());
        if (Revision.Len() != 8 && Revision.Len() != 21) return false;
        for (TCHAR C : Revision.Left(8)) if (C < TEXT('0') || C > TEXT('9')) return false;
        if (!FDateTime::Validate(FCString::Atoi(*Revision.Left(4)), FCString::Atoi(*Revision.Mid(4,2)),
            FCString::Atoi(*Revision.Mid(6,2)), 0, 0, 0, 0)) return false;
        if (Revision.Len() == 21)
        {
            if (Revision[8] != TEXT('_')) return false;
            for (TCHAR C : Revision.Right(12))
                if (!((C >= TEXT('0') && C <= TEXT('9')) || (C >= TEXT('a') && C <= TEXT('f')))) return false;
        }
        return true;
    }
    // A fresh wrapper revision gets its own storage; never import or migrate a shared capital draft.
    inline FString PrivateReviewDraftRelativePath(const FString& Package)
    {
        return IsCitadelHumanReview(Package)
            ? TEXT("WorldEdit/PrivateReviews/") + Package.RightChop(FString(TEXT("/Game/WorldRebuild/")).Len()) + TEXT("/draft.json")
            : FString();
    }
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
    inline FString OrdinaryDraftRelativePath(const FString& Package)
    {
        const FString Review = PrivateReviewDraftRelativePath(Package);
        if (!Review.IsEmpty()) return Review;
        const FString Prefix = TEXT("/Game/WorldRebuild/");
        return IsCitadelCampaign(Package)
            ? TEXT("WorldEdit/") + Package.Mid(Prefix.Len(), FString(TEXT("AegisCitadel_")).Len() + 12) + TEXT("/draft.json")
            : FString();
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
            || (IsCitadelCampaign(SelectedMap) && Package == SelectedMap)
            || (IsCitadelHumanReview(Package) && Package.Equals(SelectedMap, ESearchCase::CaseSensitive));
    }
}
