#pragma once

#include "CoreMinimal.h"

class IConsoleVariable;

namespace WarCitadelLumenStudyRuntime
{
    bool Recipe(const FString& Mode,TMap<FString,int32>& Values);
    void ReviewRecipe(TMap<FString,int32>& Values);

    /** Temporary, tagged CVar history; restores earlier settings without saving them. */
    class FOverride final
    {
    public:
        FOverride();
        ~FOverride();
        FOverride(const FOverride&)=delete;
        FOverride& operator=(const FOverride&)=delete;
        bool Apply(const TMap<FString,int32>& Values,FString& Error);
        void Restore();
    private:
        FName Tag;
        TArray<IConsoleVariable*> Changed;
    };
}
